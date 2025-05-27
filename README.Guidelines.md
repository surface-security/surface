# Surface Security Guidelines

Surface Security is an open source security intelligence and automation platform, empowering Security Engineers around the world.

This project should provide a great base to allow teams and engineers to expand its capabilities to create a centralized inventory of all IT assets, applications, infrastructure and more. This repository contains general guidelines to contribute to the project, instructions on how we are working on it and other information on governance.

**If you are looking for specific instructions on how to contribute to one specific project this is not the correct place to look into.**

# Prioritising

We are currently working on ways to convert our roadmap into public. Until then, part of the workflow is invisible to most, but the way items get prioritised in `Surface-Security` is as follows:
1. All new issues assigned to the "Roadmap" project get pushed to backlog type of bucket;
1. Every quarter, the core team of the project will review that bucket and choose items that make sense to focus on the following quarter;
1. Bugs breaking a production build have priority for fixing;
1. Minor bugs should have priority over features in each quarter plan, but not during the cycle.

## Feature Requests and Bugs

Anyone is welcome to open new issues in the respective projects - and in fact we appreciate your help in reporting bugs, suggesting new features or raising concerns overall - but please be mindful when opening new tickets. This is still a volunteering initiative and it's easy to get lost in crazy amounts of tickets to process.

**Please fill in the requested templates, so it's easier for us to identify the source of the issue, the type of feature request, ask questions and so on.**


# Contributing

Anyone is welcome to contribute with code to all repositories. The below are some of the common and transversal rules for Surface Security repositories:

- We promote [feature branch type of development](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches): clone the repository, create a new branch and open a pull request against your branch;
- Write [good commit messages](https://initialcommit.com/blog/git-commit-messages-best-practices), good pull request descriptions, follow the issue templates as close as possible, and be an overall good citizen in this public space. Although we do not have a specific convention, it should be clear what is changing, or what is the request, or why a pull request matters;
- All projects should leverage semantic versioning, git tags and git releases to publish packages. When preparing a new release, use [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) for reference on what headings the new release should contain. We might take more than one change before releasing a new version, depending on the level of breaking changes or not;

**When not specified, the default contributing guidelines should fall into [Surface's](https://github.com/surface-security/surface/wiki/Contributing-Guidelines).**


## Releases

This section describes the release process for the different repository types present in this GitHub organization. 
There are four types of repositories in this organization:
1. Apps (Surface)
1. Libs/Django Apps (`django-abc`)
1. Scanners (`scanner-abc`)
1. Utility apps

An important regard in this topic is **all releases should follow the [semver](https://semver.org) guidelines.

**[Surface](https://github.com/surface-security/surface)** enjoys being the end product and therefore it contains the most straightforward process of them all:
- Devs create their branch and open pull requests against the default branch (`main`). This process creates a temporary package that is pushed to the GitHub repository, in case we need to test the final build or check the end product.
- Code is reviewed, approved and merged. This does not publish a new package.
- When maintainers want a new release of the application, they have to use git tags and GitHub releases to produce a final package that gets published into the GitHub registry. This tag will be consumed by GitHub actions to know which version to publish.

**Other library-style apps** enjoy a different, more controlled process:
- Devs create tehir branch and open pull requests against the default branch (which is **`develop`** in this case). No package is produced at this stage, neither after merge.
- When maintainers have sufficient changes and/or want to create a release candidate (`rc`) for field testing, they have to create a git tag and a release to push the build to the registry.
    - If we need to fix things in `rc` builds, we just expand on that: `rc1`, `rc2`, `rc3` and so on, as many as necessary.
- After some field testing, maintainers can publish an official build, leveraging the same process: git tags and release. 


# Documentation

The project's README should have quick start guides to get users going but the project should have a comprehensive set of instructions to run, develop and contribute to the project in the Wiki tab. Example: https://github.com/surface-security/surface/wiki

The project's documentation must be comprehensive, consider different expertise and experience levels, and should contain the required instructions to allow users to install, set up and have the module or application running. More specifically, it should list required steps to build, optional tweaks users can use, and code samples when necessary to explain the concepts. Never be **cheap** on docs.
