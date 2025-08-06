# Security Checklist for Parts Tracker Deployment

This checklist ensures secure deployment across all environments.

## 🔐 Environment Variables & Secrets

### ✅ Before Deployment

- [ ] **Generate Secure Secrets**: Use `generate-secrets.sh` or `generate-secrets.bat`
- [ ] **Verify .env Files**: No hardcoded passwords in any `.env` files
- [ ] **Check Git Status**: Ensure no `.env` files are tracked by Git
- [ ] **Validate Secret Strength**: All passwords minimum 24 characters
- [ ] **Unique Secrets**: Different secrets for each environment

### ✅ Environment File Security

```bash
# Check that .env files have proper permissions
ls -la .env*
# Should show: -rw------- (600 permissions)

# Verify .env files are gitignored
git status --ignored | grep .env

# Confirm no secrets in repository history
git log --all --full-history -- "*.env"
```

## 🗄️ Database Security

### ✅ PostgreSQL Configuration

#### Local Development
- [ ] **Non-default Passwords**: Change from example passwords
- [ ] **Firewall Rules**: Only necessary ports exposed
- [ ] **User Separation**: Separate users for app vs Power BI

#### Production
- [ ] **SSL Connections**: Enable SSL for all connections
- [ ] **Network Isolation**: Database not publicly accessible
- [ ] **Read-only Users**: Power BI uses read-only account
- [ ] **Connection Limits**: Configure max_connections appropriately
- [ ] **Backup Strategy**: Automated backups configured

### ✅ Power BI Integration

```sql
-- Verify Power BI user has minimal privileges
\du powerbi_reader

-- Check table access
SELECT grantee, table_name, privilege_type 
FROM information_schema.table_privileges 
WHERE grantee = 'powerbi_reader';

-- Ensure no write permissions
SELECT grantee, privilege_type 
FROM information_schema.usage_privileges 
WHERE grantee = 'powerbi_reader';
```

## 🐳 Container Security

### ✅ Docker Configuration

- [ ] **Non-root Users**: All containers run as non-root
- [ ] **Minimal Images**: Using slim/alpine base images
- [ ] **Vulnerability Scanning**: Regular security scans
- [ ] **Secrets Management**: No secrets in Dockerfiles
- [ ] **Health Checks**: All containers have health checks

### ✅ Network Security

- [ ] **Internal Networks**: Services communicate on internal networks
- [ ] **Port Exposure**: Only necessary ports exposed externally
- [ ] **SSL/TLS**: HTTPS enforced for all external communication
- [ ] **CORS Configuration**: Restrictive CORS policy

## ☁️ Azure Security

### ✅ Container Apps

- [ ] **Managed Identity**: Using managed identities where possible
- [ ] **Key Vault Integration**: Secrets stored in Azure Key Vault
- [ ] **Network Policies**: Ingress/egress rules configured
- [ ] **SSL Certificates**: Managed certificates enabled
- [ ] **Logging**: Comprehensive logging enabled

### ✅ Azure Database for PostgreSQL

- [ ] **Firewall Rules**: Restrictive firewall configuration
- [ ] **SSL Enforcement**: SSL connections required
- [ ] **Backup Retention**: Appropriate backup retention period
- [ ] **Monitoring**: Database insights enabled
- [ ] **Threat Protection**: Advanced threat protection enabled

## 🔒 Application Security

### ✅ Django Security Settings

```python
# Verify security settings in settings_azure.py
DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')  # From environment
ALLOWED_HOSTS = [...]  # Specific hosts only
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

### ✅ Authentication & Authorization

- [ ] **Strong Passwords**: Password policy enforced
- [ ] **Session Security**: Secure session configuration
- [ ] **CSRF Protection**: CSRF tokens implemented
- [ ] **XSS Protection**: Input sanitization and output encoding
- [ ] **SQL Injection**: Parameterized queries used

## 📊 Monitoring & Auditing

### ✅ Security Monitoring

- [ ] **Access Logs**: All access logged and monitored
- [ ] **Failed Login Tracking**: Failed authentication attempts logged
- [ ] **Database Activity**: Database access monitored
- [ ] **Container Metrics**: Resource usage monitored
- [ ] **Security Alerts**: Automated security alerts configured

### ✅ Audit Trail

```bash
# Check Django audit logs
docker logs backend | grep -i "auth\|login\|error"

# Check PostgreSQL logs
docker exec postgres tail -f /var/log/postgresql/*.log

# Check container security events
docker events --filter type=container --since 24h
```

## 🚨 Incident Response

### ✅ Security Incident Preparation

- [ ] **Contact List**: Security team contacts documented
- [ ] **Runbooks**: Incident response procedures documented
- [ ] **Backup Access**: Emergency access procedures documented
- [ ] **Recovery Plans**: Disaster recovery plans tested
- [ ] **Communication Plan**: Stakeholder notification procedures

### ✅ Regular Security Tasks

#### Weekly
- [ ] Review access logs for anomalies
- [ ] Check for failed login attempts
- [ ] Verify backup integrity
- [ ] Monitor resource usage

#### Monthly
- [ ] Rotate service passwords
- [ ] Update container images
- [ ] Review user permissions
- [ ] Security scan all containers

#### Quarterly
- [ ] Full security audit
- [ ] Penetration testing
- [ ] Disaster recovery testing
- [ ] Security training updates

## 🛠️ Security Tools & Commands

### Environment Security Check
```bash
# Check for exposed secrets
./security-scan.sh

# Verify environment variables
env | grep -i "secret\|password\|key" | wc -l

# Check file permissions
find . -name "*.env*" -exec ls -la {} \;
```

### Container Security Scan
```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image parts-tracker-backend

# Check container configurations
docker run --rm -it --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --label docker_bench_security \
  docker/docker-bench-security
```

### Network Security Check
```bash
# Check open ports
nmap -sS -O target_ip

# Verify SSL configuration
sslscan your-domain.com

# Check CORS policy
curl -H "Origin: https://malicious-site.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS https://your-api.com/api/
```

## 📋 Deployment Security Checklist

### Before First Deployment
- [ ] All secrets generated using secure methods
- [ ] Environment files properly configured
- [ ] SSL certificates obtained and configured
- [ ] Firewall rules configured
- [ ] Monitoring and logging enabled

### Before Each Deployment
- [ ] Security scan of all container images
- [ ] Environment variables validated
- [ ] Database backup created
- [ ] Rollback plan prepared
- [ ] Security team notified

### After Each Deployment
- [ ] Health checks passing
- [ ] Security monitoring active
- [ ] Access logs being generated
- [ ] SSL certificates valid
- [ ] Performance baselines established

## 🔗 Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [PostgreSQL Security Best Practices](https://www.postgresql.org/docs/current/security.html)
- [Azure Security Center](https://docs.microsoft.com/en-us/azure/security-center/)
- [Container Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Remember**: Security is an ongoing process, not a one-time setup. Regularly review and update your security measures as threats evolve.