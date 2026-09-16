# Common Issues

Solutions for frequently encountered problems.

!!! tip "Demo Mode Examples"
    In demo mode, you can see these common scenarios:

    - **Parts stuck at step**: INJ-0042-025 blocked at Assembly pending FPI approval
    - **Permission restrictions**: Customer Tom Bradley can only see Midwest Fleet orders
    - **Training block**: Dave Wilson can't work at Flow Testing (expired certification)
    - **Calibration alert**: Torque Wrench TW-25 shows overdue, equipment usage blocked
    - **Pending approval**: APR-2024-0015 awaiting Jennifer Walsh's sign-off

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

Parts advance automatically once a step's requirements are met, so "stuck"
always means something is still outstanding. Check in this order — the first
cause is by far the most common and the least obvious:

1. **Another part in the same lot isn't finished.** Parts that haven't been
   split advance *together* — all parts at the same work order and step, or
   none. One unfinished part holds the whole lot. Look at the other parts
   before looking at this one.
2. **The step's First Piece Inspection is pending.** An unsigned FPI blocks
   every part at that step.
3. **A required capture is missing.** Open the step's review screen; it shows
   which.
4. **The part is quarantined.** It won't move until a disposition is decided.
5. **The operator isn't trained for the step**, so the work can't be completed
   or assigned.
6. **A completion at that step was voided.** The gate ignores voided rows, so
   the part waits for the work to be redone. Expand the part's traveler and
   look for a red **"N voided"** badge on the step — see [Running Work
   Instructions](../workflows/dwi/running.md#voiding-a-completion).

    If several parts stalled at once, suspect a **shared cycle** — voiding a
    batch record (wash, heat treat, plating) retracts it for every part in
    that load, so the whole load blocks together.

!!! tip "A pending sampling decision is not the cause"
    If a substep's sampling rule can't decide yet, the part advances
    tentatively rather than blocking. A pending decision never holds a part.

### Can't complete a step
**Cause**: Missing permissions or incomplete captures

**Solutions**:
1. Verify the user has `change_parts` and `add_measurementresult`
2. Complete any required captures — the review screen lists what's outstanding
3. If a substep genuinely doesn't apply, use **Mark N/A** with a reason
   (unless it's safety-critical, which can never be N/A)
4. Resolve pending approvals and release hold points

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
1. Verify Microsoft Entra ID app configuration
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
**Cause**: The URL doesn't match any page, or the record it names doesn't
exist.

**Solutions**:
1. Check the URL is complete — a link truncated in chat or email is the most
   common cause
2. The record may have been deleted or belongs to another tenant
3. Navigate from a page you know rather than editing the URL

### "This link isn't valid"
**Cause**: The URL is the right shape but one of its values isn't — usually a
truncated or mistyped record id in a pasted link.

The message names which parameter is wrong.

**Solution**: Get the link again from its source rather than repairing it by
hand. Ids are not guessable, and editing one digit lands you on a different
record rather than the one you wanted.

### A filtered list looks wrong, or a filter you didn't set is applied

**Cause**: Filters live in the URL, so a bookmarked or shared link carries
whoever's filters were active when it was copied.

**Solution**: Clear the filters, or open the page from the sidebar to start
clean. A filter value that is no longer valid is dropped and the full list
renders, so a stale link degrades to "unfiltered" rather than to an error.

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
