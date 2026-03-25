# Odoo 18 Development Environment with MailHog

Môi trường phát triển Odoo 18 với tích hợp MailHog để test email functionality.

## 🚀 Quick Start

```bash
# Start all services
docker-compose up -d

# Access Odoo
http://localhost:8069

# Access MailHog (Email Testing UI)
http://localhost:8025
```

## 📧 MailHog Integration

### MailHog là gì?
MailHog là một SMTP testing tool cho phép bạn:
- **Capture tất cả outgoing emails** từ Odoo
- **View emails trong web interface** thay vì gửi email thật
- **Test email functionality** mà không spam real users
- **Debug email templates** và content

### Cấu hình
- **SMTP Server**: `mailhog` (internal Docker hostname)
- **SMTP Port**: `1025`
- **Web UI**: `http://localhost:8025`
- **Email From**: `dev@localhost.localdomain`

## 🔧 Services

| Service | Port | Description |
|---------|------|-------------|
| Odoo | 8069, 5678 | Odoo web interface và debug port |
| PostgreSQL | 5432 | Database server |
| MailHog SMTP | 1025 | Internal SMTP server ( không expose ra host) |
| MailHog Web UI | 8025 | Web interface để xem emails |

## 📋 How to Use MailHog

### 1. Start Environment
```bash
docker-compose up -d
```

### 2. Test Email Functionality
Trong Odoo:
- Test user registration emails
- Test password reset emails
- Test notification emails
- Test report generation emails
- Test any other email functionality

### 3. View Emails
1. Mở trình duyệt: `http://localhost:8025`
2. Xem tất cả captured emails trong inbox
3. Click vào email để xem content (HTML/Plain text/Source)
4. Download, delete, hoặc release emails nếu cần

### 4. Email Testing Scenarios

#### Test User Registration
1. Tạo user mới trong Odoo
2. Check MailHog UI cho welcome email
3. Verify email content và formatting

#### Test Password Reset
1. Go to Odoo login page
2. Click "Forgot Password?"
3. Enter email address
4. Check MailHog cho reset email

#### Test Notifications
1. Trigger Odoo notifications (e.g., approval workflows)
2. Check MailHog cho notification emails

#### Test Report Emails
1. Generate reports trong Odoo với email delivery
2. Check MailHog cho report attachments

## 🔍 MailHog Features

### Email Viewing
- **HTML View**: Render HTML emails correctly
- **Plain Text**: View text-only version
- **Source**: View raw email source
- **MIME**: View email structure và attachments

### Email Management
- **Delete**: Remove individual emails hoặc delete all
- **Download**: Save email source files
- **Search**: Search emails by content, sender, recipient
- **Release**: Forward emails to real SMTP server (advanced)

### Real-time Updates
- MailHog UI updates real-time khi emails arrive
- No refresh needed
- Event stream connection status indicator

## 🛠️ Troubleshooting

### Common Issues

#### Issue 1: Cannot access MailHog UI
```bash
# Check container status
docker-compose ps

# Check logs
docker logs mailhog

# Check port conflict
netstat -tulpn | grep :8025
```

#### Issue 2: Emails not appearing in MailHog
```bash
# Check Odoo SMTP configuration
docker exec odoo-odoo-1 cat /etc/odoo/odoo.conf | grep smtp

# Test SMTP connection
docker exec odoo-odoo-1 python3 -c "
import smtplib
server = smtplib.SMTP('mailhog', 1025)
server.noop()
print('SMTP OK')
server.quit()
"
```

#### Issue 3: Odoo cannot connect to MailHog
```bash
# Check network connectivity
docker exec odoo-odoo-1 curl -f http://mailhog:8025

# Restart services
docker-compose restart mailhog odoo
```

### Debug Commands
```bash
# View container logs
docker logs mailhog
docker logs odoo-odoo-1

# Check container connectivity
docker exec odoo-odoo-1 ping mailhog  # nếu ping có sẵn

# Test SMTP manually
docker exec odoo-odoo-1 telnet mailhog 1025  # nếu telnet có sẵn
```

## 📝 Development Best Practices

### Email Testing Workflow
1. **Test trong development**: Luôn dùng MailHog để test
2. **Verify content**: Check email templates, formatting, links
3. **Test attachments**: Verify file attachments work correctly
4. **Test different scenarios**: Test cả success và error cases
5. **Performance testing**: Test bulk email sending

### Code Example - Test Email Sending
```python
# Trong Odoo environment hoặc custom script
import smtplib
from email.mime.text import MIMEText

def test_email():
    msg = MIMEText('Test email content', 'plain', 'utf-8')
    msg['Subject'] = 'Test Email'
    msg['From'] = 'dev@localhost.localdomain'
    msg['To'] = 'test@example.com'

    server = smtplib.SMTP('mailhog', 1025)
    server.send_message(msg)
    server.quit()
    print('Email sent to MailHog!')

# Test trong container
# docker exec odoo-odoo-1 python3 test_email.py
```

### Configuration Tips
- **Development only**: MailHog chỉ cho development, không dùng production
- **Email templates**: Test templates với realistic data
- **Localization**: Test emails với different languages/lôcales
- **Responsive design**: Test email rendering trên mobile devices

## 🔄 Container Management

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Rebuild Odoo
```bash
docker-compose build --no-cache odoo
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f odoo
docker-compose logs -f mailhog
```

## 🌐 Network Configuration

MailHog và Odoo chạy trong Docker network `odoo_default`.

- **Odoo hostname**: `odoo-odoo-1` (internal)
- **MailHog hostname**: `mailhog` (internal)
- **PostgreSQL hostname**: `postgres` (internal)

Host machine access:
- **Odoo**: `http://localhost:8069`
- **MailHog UI**: `http://localhost:8025`

## 🔐 Security Notes

- **MailHog chỉ cho development**: Không expose SMTP port ra internet
- **Email data**: Emails stored in memory (mất khi container restart)
- **No authentication**: MailHog UI không có authentication (development only)
- **Network isolation**: Containers isolated trong Docker network

## 📚 Additional Resources

- [MailHog Documentation](https://github.com/mailhog/MailHog)
- [Odoo Email Configuration](https://www.odoo.com/documentation/18.0/applications/communication/email.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🆘 Support

Nếu gặp issues:
1. Check Docker logs: `docker-compose logs`
2. Verify port availability
3. Check network connectivity
4. Test SMTP connection manually
5. Restart services: `docker-compose restart`

---

**Version**: Odoo 18.0 + MailHog latest
**Last Updated**: 2025-11-06
**Environment**: Development/Testing