#!/usr/bin/env node
import * as cdk from '@aws-cdk/core';
import { SurfStack } from '../lib/surf-stack';

const app = new cdk.App();
new SurfStack(app, 'SurfStack');
