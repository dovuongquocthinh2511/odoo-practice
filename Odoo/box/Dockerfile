# Odoo base with Python 3.10+
# version 3.1

FROM odoo:18

# Install git, CA certificates, and Python packages
USER root
RUN apt-get update && \
    apt-get install -y \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    update-ca-certificates

# Install all Python packages first (with --break-system-packages for Python 3.12+)
# Use --trusted-host to bypass SSL verification for PyPI
RUN pip install --break-system-packages --ignore-installed \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    fastapi \
    python-multipart \
    ujson \
    a2wsgi \
    parse-accept-language \
    PyJWT \
    python-jose \
    python-dotenv \
    pdfplumber \
    python-docx \
    htmldocx \
    Unidecode \
    pikepdf \
    aiohttp \
    cachetools \
    Cerberus \
    apispec \
    jsondiff \
    pyquerystring \
    requests \
    debugpy

# Fix permissions for sessions directory
RUN mkdir -p /var/lib/odoo/sessions && \
    chown -R odoo:odoo /var/lib/odoo/sessions && \
    chmod 700 /var/lib/odoo/sessions

USER odoo


