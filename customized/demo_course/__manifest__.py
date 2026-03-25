# -*- coding: utf-8 -*-
{
    'name': 'Demo Course',
    'summary': """Demo model @ relation & api decorator""",
    'description': """Demo model @ relation & api decorator""",
    'author': 'minhng.info',
    'maintainer': 'minhng.info',
    'website': 'https://minhng.info',
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': [],
    'data': [
        'security/ir.model.access.csv', # <- khai báo security
        'views/course_views.xml', # <- khai báo view
    ],
    'demo': [],
    'css': [],
    # 'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
