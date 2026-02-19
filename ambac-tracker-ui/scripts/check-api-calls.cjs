#!/usr/bin/env node
/**
 * Script to check for potentially incorrect Zodios API call patterns.
 *
 * Zodios can behave inconsistently with query parameters. The safest pattern is:
 * - Always use { queries: { param: value } } for query parameters
 * - Use { params: { id: value } } for path parameters
 *
 * This script finds API calls that might be missing the queries wrapper.
 *
 * Run: npm run check:api
 */

const fs = require('fs');
const path = require('path');

// Known query parameter names - add more as needed
const REQUIRED_QUERY_PARAMS = [
  'measurement_id',
  'part_id',
  'work_order_id',
  'equipment_id',
  'content_type',
  'object_id',
];

// These are usually optional and have defaults, but still good to wrap
const OPTIONAL_QUERY_PARAMS = [
  'days',
  'limit',
  'offset',
  'ordering',
  'search',
  'min_occurrences',
  'subgroup_size',
];

// Endpoints known to work without queries wrapper (all params optional with defaults)
const SAFE_ENDPOINTS = [
  'api_dashboard_', // Dashboard endpoints have all optional params
  'api_content_types_list',
];

function findFiles(dir, extensions) {
  const files = [];
  try {
    const items = fs.readdirSync(dir, { withFileTypes: true });
    for (const item of items) {
      const fullPath = path.join(dir, item.name);
      if (item.isDirectory() && !item.name.startsWith('.') && item.name !== 'node_modules') {
        files.push(...findFiles(fullPath, extensions));
      } else if (item.isFile() && extensions.some(ext => item.name.endsWith(ext))) {
        files.push(fullPath);
      }
    }
  } catch (e) {
    // Ignore permission errors
  }
  return files;
}

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const issues = [];

  // Find api.api_xxx({ ... }) calls - handle multiline
  const fullContent = content;

  // More robust regex to find API calls
  const apiCallPattern = /api\.(api_[\w]+)\s*\(\s*\{/g;
  let match;

  while ((match = apiCallPattern.exec(fullContent)) !== null) {
    const methodName = match[1];
    const startIdx = match.index;

    // Skip known safe endpoints
    if (SAFE_ENDPOINTS.some(safe => methodName.startsWith(safe))) {
      continue;
    }

    // Find the matching closing brace (simplified - assumes well-formed code)
    let braceCount = 1;
    let endIdx = match.index + match[0].length;
    while (braceCount > 0 && endIdx < fullContent.length) {
      if (fullContent[endIdx] === '{') braceCount++;
      if (fullContent[endIdx] === '}') braceCount--;
      endIdx++;
    }

    const callContent = fullContent.substring(match.index, endIdx + 1);
    const lineNumber = fullContent.substring(0, startIdx).split('\n').length;

    // Check if call has queries wrapper
    const hasQueriesWrapper = /queries\s*:\s*\{/.test(callContent);
    const hasParamsWrapper = /\bparams\s*:\s*\{/.test(callContent);

    // Check for required query params without queries wrapper
    for (const param of REQUIRED_QUERY_PARAMS) {
      const paramPattern = new RegExp(`(?<!queries\\s*:\\s*\\{[^}]*)\\b${param}\\s*:`);
      if (paramPattern.test(callContent) && !hasQueriesWrapper) {
        issues.push({
          line: lineNumber,
          method: methodName,
          param,
          type: 'error',
          message: `Required query param '${param}' should be in queries: { }`,
        });
      }
    }

    // Warn about optional params if combined with params: (path params)
    if (hasParamsWrapper && !hasQueriesWrapper) {
      for (const param of OPTIONAL_QUERY_PARAMS) {
        const paramPattern = new RegExp(`\\b${param}\\s*:`);
        if (paramPattern.test(callContent)) {
          issues.push({
            line: lineNumber,
            method: methodName,
            param,
            type: 'warning',
            message: `Query param '${param}' should be in queries: { } when used with params:`,
          });
        }
      }
    }
  }

  return issues;
}

function main() {
  const srcDir = path.join(__dirname, '..', 'src');
  const files = findFiles(srcDir, ['.ts', '.tsx']);

  let errors = 0;
  let warnings = 0;
  const allIssues = [];

  for (const file of files) {
    const issues = checkFile(file);
    if (issues.length > 0) {
      const relPath = path.relative(path.join(__dirname, '..'), file);
      for (const issue of issues) {
        allIssues.push({ file: relPath, ...issue });
        if (issue.type === 'error') errors++;
        else warnings++;
      }
    }
  }

  // Print grouped by file
  const byFile = {};
  for (const issue of allIssues) {
    if (!byFile[issue.file]) byFile[issue.file] = [];
    byFile[issue.file].push(issue);
  }

  for (const [file, issues] of Object.entries(byFile)) {
    console.log(`\n${file}:`);
    for (const issue of issues) {
      const icon = issue.type === 'error' ? '❌' : '⚠️';
      console.log(`  ${icon} Line ${issue.line}: ${issue.message}`);
      console.log(`     in ${issue.method}()`);
    }
  }

  console.log('\n' + '─'.repeat(60));
  if (errors > 0) {
    console.log(`\n❌ Found ${errors} error(s) and ${warnings} warning(s).`);
    console.log('\nFix pattern: wrap query params in { queries: { ... } }');
    console.log('Example: api.method({ queries: { measurement_id: id } })');
    process.exit(1);
  } else if (warnings > 0) {
    console.log(`\n⚠️  Found ${warnings} warning(s) - review these manually.`);
    process.exit(0);
  } else {
    console.log('\n✅ No API call issues found.');
  }
}

main();
