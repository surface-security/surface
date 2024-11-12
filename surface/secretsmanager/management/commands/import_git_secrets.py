import os
import subprocess
import hashlib
from django.core.management.base import BaseCommand
from secretsmanager.models import Secret, SecretLocation
from inventory.models import GitSource

class Command(BaseCommand):
    help = 'Import secrets from git repository history'

    def add_arguments(self, parser):
        parser.add_argument('repo_path', type=str, help='Path to the git repository')
        parser.add_argument('--org', type=str, default='your-org', help='GitHub organization name')

    def get_default_branch(self, repo_path):
        """Get the default branch of the repository"""
        try:
            result = subprocess.run(
                f"git -C {repo_path} rev-parse --abbrev-ref HEAD",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return 'main'
    def scan_git_history(self, repo_path):
        """Scan git history for sensitive files"""
        allowed_formats = [
            # Cryptographic & Certificate Files
            ".jks", ".p12", ".pfx", ".pem", ".crt", ".cer", 
            ".key", ".keystore", ".csr", ".der", ".spc",
            
            # Mobile & App Signing
            ".mobileprovision", ".keychain", ".provisionprofile",
            ".apk.sign", ".aab.sign",
            
            # Configuration & Credentials
            ".env", ".conf", ".config", ".ini", ".properties",
            ".secret", ".secrets", ".credentials", ".creds",
            ".htpasswd", ".netrc",
            
            # Cloud & Infrastructure
            ".aws", "config", ".npmrc", ".tfstate", ".tfvars"
        ]

        env_variations = [f".env.{env}" for env in ["dev", "development", "prod", "production", "staging", "test", "local"]]
        allowed_formats.extend(env_variations)
        
        try:
            self.stdout.write("Getting all commits...")
            commits_result = subprocess.run(
                f"git -C {repo_path} rev-list --all",
                stdout=subprocess.PIPE,
                shell=True,
                text=True,
                check=True
            )
            commits = commits_result.stdout.splitlines()
            
            self.stdout.write(f"Found {len(commits)} commits")

            for commit in commits:
                self.stdout.write(f"Processing commit: {commit[:8]}...")

                files_result = subprocess.run(
                    f"git -C {repo_path} ls-tree -r {commit}",
                    stdout=subprocess.PIPE,
                    shell=True,
                    text=True,
                    check=True
                )

                files = []
                for line in files_result.stdout.splitlines():
                    try:
                        mode, type, hash, path = line.split(None, 3)
                        files.append(path)
                    except ValueError:
                        continue

                self.stdout.write(f"Files in commit {commit[:8]}: {files}")

                sensitive_files = [
                    f for f in files 
                    if any(f.lower().endswith(ext.lower()) for ext in allowed_formats)
                ]
                
                if sensitive_files:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Found sensitive files in {commit[:8]}: {sensitive_files}"
                        )
                    )
                    
                    for file_path in sensitive_files:
                        author = subprocess.run(
                            f"git -C {repo_path} log -1 --format=%ae {commit} -- {file_path}",
                            stdout=subprocess.PIPE,
                            shell=True,
                            text=True
                        ).stdout.strip()
                        
                        date = subprocess.run(
                            f"git -C {repo_path} log -1 --format=%aI {commit} -- {file_path}",
                            stdout=subprocess.PIPE,
                            shell=True,
                            text=True
                        ).stdout.strip()

                        yield {
                            'commit': commit,
                            'file': file_path,
                            'author': author,
                            'date': date
                        }

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Error scanning git history: {e}"))

    def calculate_file_hash(self, repo_path, commit_hash, file_path):
        """Calculate SHA256 hash of file content at specific commit"""
        try:
            result = subprocess.run(
                f"git -C {repo_path} show {commit_hash}:{file_path}",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=True
            )
            content = result.stdout
            return hashlib.sha256(content).hexdigest()
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Error reading file {file_path}: {e}"))
            return None

    def handle(self, *args, **options):
        repo_path = options['repo_path']
        self.org = options['org']

        self.stdout.write(f"Scanning repository: {repo_path}")
        
        repo_name = os.path.basename(repo_path)
        repo_url = f"https://github.com/{self.org}/{repo_name}"
        default_branch = self.get_default_branch(repo_path)
        
        git_source, _ = GitSource.objects.get_or_create(
            repo_url=repo_url,
            defaults={'branch': default_branch}
        )

        # Track files by their hash
        secret_sources = {}
        
        # First, collect all instances of each secret
        for file_info in self.scan_git_history(repo_path):
            file_hash = self.calculate_file_hash(
                repo_path, 
                file_info['commit'], 
                file_info['file']
            )
            
            if not file_hash:
                continue

            source_data = {
                "commit": file_info['commit'],
                "file": file_info['file'],
                "email": file_info['author'],
                "repository": repo_url,
                "timestamp": file_info['date'],
                "line": "1"
            }

            if file_hash not in secret_sources:
                secret_sources[file_hash] = {
                    "sources": [],
                    "file_type": os.path.splitext(file_info['file'])[1]
                }
            secret_sources[file_hash]["sources"].append(source_data)

        secrets_found = 0
        for file_hash, data in secret_sources.items():
            secret, created = Secret.objects.update_or_create(
                secret=file_hash,
                source='git-history-scan',
                git_source=git_source,
                defaults={
                    'kind': f"SensitiveFile ({data['file_type']})",
                    'verified': False,
                    'environment': 'Unknown',
                    'team': 'Unknown',
                }
            )

            # Create locations for each instance
            for source in data["sources"]:
                SecretLocation.objects.update_or_create(
                    secret=secret,
                    file_path=source['file'],
                    commit=source['commit'],
                    defaults={
                        'repository': source['repository'],
                        'timestamp': source['timestamp'],
                        'author': source['email'],
                        'line': source['line']
                    }
                )

            secrets_found += len(data["sources"])

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {secrets_found} instances of secrets from {repo_path}'
            )
        )