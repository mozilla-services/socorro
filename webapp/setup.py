from setuptools import setup, find_packages

setup(
    name='Socorro',
    version="0.1a",
    description="Breakpad Server",
    author="Robert Sayre",
    author_email="sayrer@gmail.com",
    url="http://code.google.com/p/socorro/",
    install_requires=["Pylons>=0.9.4", "SQLAlchemy>=0.3", "Genshi>=0.3.6",
                      "Authkit>=0.3.0pre5"],
    packages=find_packages(),
    include_package_data=True,
    test_suite = 'nose.collector',
    package_data={'socorro': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
    [paste.app_factory]
    main=socorro:make_app
    [paste.app_install]
    main=paste.script.appinstall:Installer
    """,
)
