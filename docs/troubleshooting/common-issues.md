# Common Issues

Solutions for frequently encountered problems.

## Login Issues

### "Invalid credentials"
**Cause**: Wrong email or password

**Solutions**:
1. Check email spelling
2. Reset password via "Forgot Password"
3. Check Caps Lock
4. Contact admin if account locked

### "Account deactivated"
**Cause**: Account has been disabled

**Solution**: Contact your administrator to reactivate.

### SSO redirect fails
**Cause**: Browser or IdP issue

**Solutions**:
1. Clear browser cache and cookies
2. Try incognito/private mode
3. Verify IdP is accessible
4. Check with IT department

### "Access denied" after login
**Cause**: Account exists but no permissions

**Solution**: Contact administrator to assign appropriate groups.

## Permission Issues

### "You don't have permission"
**Cause**: Missing required permission

**Solutions**:
1. Check with admin about your role
2. Verify you're in correct group
3. Request permission if needed

### Can't see expected data
**Cause**: Role type restrictions

**Solutions**:
1. Customer users only see their orders
2. Check tenant selection (multi-tenant)
3. Verify data exists in system

## Data Issues

### Parts stuck at step
**Cause**: Requirements not met

**Check**:
- Required measurements recorded?
- Approval pending?
- FPI required but not passed?
- Hold point active?

### Can't move parts forward
**Cause**: Missing permissions or requirements

**Solutions**:
1. Verify user has `change_parts` permission
2. Complete required measurements
3. Resolve pending approvals
4. Release hold points

### Order not showing on Tracker
**Cause**: Filter or status issue

**Solutions**:
1. Check filters are cleared
2. Verify order status (not Draft)
3. Search by order number
4. Check correct tenant selected

## Document Issues

### Can't upload document
**Cause**: File or permission issue

**Check**:
- File type supported?
- File size within limit?
- User has upload permission?

### Document stuck in "Pending Approval"
**Cause**: Awaiting approver action

**Solutions**:
1. Check approval status
2. Contact approvers
3. Recall and resubmit if needed

### Can't view document
**Cause**: Visibility restriction

**Solutions**:
1. Check document visibility level
2. Request access from owner
3. Contact admin for permission

## Performance Issues

### Slow page loading
**Causes**: Network, data volume, browser

**Solutions**:
1. Check internet connection
2. Clear browser cache
3. Try different browser
4. Use filters to reduce data
5. Contact support if persistent

### 3D model won't load
**Causes**: File size, browser, format

**Solutions**:
1. Wait for full load (check progress)
2. Try different browser (Chrome recommended)
3. Check model file size
4. Verify format compatibility

### Export taking too long
**Cause**: Large data volume

**Solutions**:
1. Apply filters before export
2. Reduce date range
3. Export will continue in background
4. Check email for download link

## Integration Issues

### HubSpot sync not working
**Causes**: Configuration, credentials, mapping

**Solutions**:
1. Check integration status in Settings
2. Verify API credentials
3. Review error log
4. Re-authorize connection

### SSO not connecting
**Causes**: Configuration, IdP issue

**Solutions**:
1. Verify Azure AD app configuration
2. Check redirect URIs match
3. Review SSO error messages
4. Contact IT for IdP issues

## Mobile Issues

### Interface looks wrong
**Cause**: Screen size, browser

**Solutions**:
1. Use modern mobile browser
2. Try landscape mode for tables
3. Use native browser (Safari/Chrome)

### Touch not responding
**Cause**: Browser or loading issue

**Solutions**:
1. Wait for page to fully load
2. Refresh page
3. Close other tabs

## Error Messages

### "Server error (500)"
**Cause**: Server-side problem

**Solutions**:
1. Wait a moment and retry
2. Refresh page
3. Contact support with details

### "Not found (404)"
**Cause**: Page or record doesn't exist

**Solutions**:
1. Check URL is correct
2. Record may have been deleted
3. Navigate from known page

### "Session expired"
**Cause**: Inactivity timeout

**Solution**: Log in again. Work in progress should be saved.

## Getting More Help

If issue persists:
1. Note exact error message
2. Note steps to reproduce
3. Take screenshot if helpful
4. Contact support with details

See [Getting Help](help.md) for support contact.
