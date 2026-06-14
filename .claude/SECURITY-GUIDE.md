# Security Configuration Guide

## Overview
This project implements security best practices for Claude Code development environment.

## Security Grade: Improved from D (42/100) to B (85/100)

### Recent Security Improvements (2025-06-14)

#### ✅ **Critical Fixes Implemented**
1. **Scoped Permissions** - Replaced wildcard permissions with specific allow/deny lists
2. **Security Monitoring** - Added real-time security hooks for suspicious activity detection
3. **Dangerous Mode Protection** - Re-enabled permission prompts for high-risk operations

#### ✅ **Security Features Active**
- **PreToolUse Hooks**: Monitors Bash, Write, Edit, and Agent tool usage
- **Security Logging**: All high-risk operations logged to `~/.claude/security-events.log`
- **Suspicious Pattern Detection**: Blocks dangerous commands automatically
- **Permission Scoping**: Denies access to sensitive files and operations

## Permission Model

### Allowed Operations (Scoped)
```json
{
  "allow": [
    "Bash(docker compose*, docker exec*, ls, cat, head, grep, find, pwd, cd, echo)",
    "Bash(npm*, npx*, yarn*, pnpm*, bun* with --timeout=300000)",
    "Read(*)",
    "Edit(*)",
    "Write(*)",
    "Glob(*)",
    "Grep(*)"
  ]
}
```

### Denied Operations (Security Boundary)
```json
{
  "deny": [
    "Bash(rm *, git push*, sudo *, mkfs *, fdisk *, dd *, chmod 000*, chown *)",
    "Bash(*~/.ssh*, */.ssh/*, ~/.aws*, */.aws/*)",
    "Read(~/.ssh/*, ~/.aws/*, /etc/passwd, /etc/shadow)",
    "Write(~/.ssh/*, ~/.aws/*, /etc/*)",
    "Edit(~/.ssh/*, ~/.aws/*, /etc/*)"
  ]
}
```

## Security Monitoring

### Real-time Protection
- **Suspicious Pattern Detection**: 15+ dangerous command patterns
- **Automatic Blocking**: High-risk operations blocked with alerts
- **Audit Trail**: All tool usage logged with timestamps

### Protected Patterns
```javascript
/rm\s+-rf/           // Force delete
/chmod\s+000/        // Remove all permissions
/dd\s+if=/           // Disk writes
/curl.*\|.*sh/       // Pipe download to shell
/eval\s*\(/          // Dynamic code execution
/~\/\.ssh\//         // SSH directory access
/sudo\s+/            // Privilege escalation
```

## Security Audit Commands

### Check Security Events
```bash
# View recent security events
tail -20 ~/.claude/security-events.log

# Filter for alerts only
grep SECURITY_ALERT ~/.claude/security-events.log

# Check for specific tool usage
grep "tool_name.*Bash" ~/.claude/security-events.log
```

### Verify Configuration
```bash
# Run security scan
npx ecc-agentshield scan

# Check permissions
cat ~/.claude/settings.json | grep -A 20 "permissions"

# Test security hooks
echo '{"toolName":"Bash","input":{"command":"rm -rf /"}}' | node ~/.claude/hooks/security-monitor.js
```

## Project-Specific Security

### API Keys Management
- ✅ **No hardcoded secrets** in configuration
- ✅ **Environment variables** used for sensitive data
- ✅ **JWT secret** moved to environment variable (critical fix)

### Docker Operations
- Allowed: `docker compose*`, `docker exec*`
- Denied: Direct system manipulation commands
- Timeout: 5 minutes for package operations

### Git Operations
- Allowed: Most git commands
- Denied: `git push*` (requires explicit permission)
- Reason: Prevents accidental push operations

## Best Practices

### For Development
1. **Never commit API keys** - Use environment variables
2. **Review security logs** regularly for suspicious activity
3. **Use scoped permissions** instead of wildcards
4. **Test security hooks** before deployment

### For Production
1. **Enable all security hooks** - No bypassing allowed
2. **Regular security audits** - Weekly security scans
3. **Monitor logs** - Set up log monitoring and alerts
4. **Update dependencies** - Keep security tools current

### For Team Collaboration
1. **Document permission changes** - Why specific access is needed
2. **Security review** - Get approval for permission changes
3. **Training** - Ensure team understands security model
4. **Incident response** - Have plan for security events

## Security Event Response

### If Security Alert Triggered
1. **Review the operation** - Was it intentional?
2. **Check the pattern** - What triggered the alert?
3. **Assess impact** - Could this cause damage?
4. **Document decision** - Why allowed/blocked?

### False Positives
If legitimate operations are blocked:
1. **Review the deny list** - Can you scope more precisely?
2. **Add exceptions** - Use specific patterns instead of wildcards
3. **Document rationale** - Why this exception is needed

## Continuous Improvement

### Regular Tasks
- [ ] Weekly: Review security events log
- [ ] Monthly: Run full security scan
- [ ] Quarterly: Update security patterns
- [ ] Bi-annually: Audit permission model

### Security Updates
- Monitor AgentShield updates
- Review new suspicious patterns
- Update deny list as needed
- Test security hook effectiveness

## Emergency Contacts

### Security Incidents
- **Critical Issues**: Immediate review required
- **Configuration Questions**: Check this guide first
- **False Positives**: Document and adjust patterns

## Security Score History

| Date | Grade | Score | Key Changes |
|------|-------|-------|-------------|
| 2025-06-14 | B | 85/100 | Scoped permissions, security hooks, monitoring |
| 2025-06-14 | D | 42/100 | Initial scan - critical vulnerabilities found |

---

**Last Updated**: 2025-06-14
**Security Grade**: B (85/100) - **Good security posture**
**Next Audit**: 2025-07-14
