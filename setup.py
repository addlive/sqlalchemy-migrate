#!/usr/bin/python
from setuptools import setup,find_packages

try:
    import buildutils
except ImportError:
    pass

setup(
    name = "sqlalchemy-migrate",
    version = "0.5.1.2",
    packages = find_packages(exclude=['test*']),
    include_package_data = True,
    description = "Database schema migration for SQLAlchemy",
    long_description = """
Inspired by Ruby on Rails' migrations, Migrate provides a way to deal with database schema changes in `SQLAlchemy <http://sqlalchemy.org>`_ projects.

Migrate extends SQLAlchemy to have database changeset handling. It provides a database change repository mechanism which can be used from the command line as well as from inside python code.
""",

    install_requires = ['sqlalchemy >= 0.5'],
    setup_requires = ['nose >= 0.10', 'sphinx >= 0.5'],

    author = "Evan Rosson",
    author_email = "evan.rosson@gmail.com",
    url = "http://code.google.com/p/sqlalchemy-migrate/",
    maintainer = "Jan Dittberner",
    maintainer_email = "jan@dittberner.info",
    license = "MIT",

    entry_points = """
    [console_scripts]
    migrate = migrate.versioning.shell:main
    migrate-repository = migrate.versioning.migrate_repository:main
    """,
    test_suite = "nose.collector",
)
