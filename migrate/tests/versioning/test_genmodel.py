# -*- coding: utf-8 -*-

import os

import sqlalchemy
from sqlalchemy import *
from nose.tools import eq_

from migrate.versioning import genmodel, schemadiff
from migrate.changeset import schema, SQLA_06

from migrate.tests import fixture


class TestSchemaDiff(fixture.DB):
    table_name = 'tmp_schemadiff'
    level = fixture.DB.CONNECT

    def _setup(self, url):
        super(TestSchemaDiff, self)._setup(url)
        self.meta = MetaData(self.engine, reflect=True)
        self.meta.drop_all()  # in case junk tables are lying around in the test database
        self.meta = MetaData(self.engine, reflect=True)  # needed if we just deleted some tables
        self.table = Table(self.table_name, self.meta,
            Column('id',Integer(), primary_key=True),
            Column('name', UnicodeText()),
            Column('data', UnicodeText()),
        )

    def _teardown(self):
        if self.table.exists():
            self.meta = MetaData(self.engine, reflect=True)
            self.meta.drop_all()
        super(TestSchemaDiff, self)._teardown()

    def _applyLatestModel(self):
        diff = schemadiff.getDiffOfModelAgainstDatabase(self.meta, self.engine, excludeTables=['migrate_version'])
        genmodel.ModelGenerator(diff,self.engine).runB2A()

    @fixture.usedb()
    def test_functional(self):

        def assertDiff(isDiff, tablesMissingInDatabase, tablesMissingInModel, tablesWithDiff):
            diff = schemadiff.getDiffOfModelAgainstDatabase(self.meta, self.engine, excludeTables=['migrate_version'])
            eq_(
                (diff.tables_missing_from_B,
                 diff.tables_missing_from_A,
                 diff.tables_different.keys(),
                 bool(diff)),
                (tablesMissingInDatabase,
                 tablesMissingInModel,
                 tablesWithDiff,
                 isDiff)
                )

        # Model is defined but database is empty.
        assertDiff(True, [self.table_name], [], [])

        # Check Python upgrade and downgrade of database from updated model.
        diff = schemadiff.getDiffOfModelAgainstDatabase(self.meta, self.engine, excludeTables=['migrate_version'])
        decls, upgradeCommands, downgradeCommands = genmodel.ModelGenerator(diff,self.engine).genB2AMigration()

        # Feature test for a recent SQLa feature;
        # expect different output in that case.
        if repr(String()) == 'String()':
            self.assertEqualsIgnoreWhitespace(decls, '''
            from migrate.changeset import schema
            pre_meta = MetaData()
            post_meta = MetaData()
            tmp_schemadiff = Table('tmp_schemadiff', post_meta,
                Column('id', Integer, primary_key=True, nullable=False),
                Column('name', UnicodeText),
                Column('data', UnicodeText),
            )
            ''')
        else:
            self.assertEqualsIgnoreWhitespace(decls, '''
            from migrate.changeset import schema
            pre_meta = MetaData()
            post_meta = MetaData()
            tmp_schemadiff = Table('tmp_schemadiff', post_meta,
                Column('id', Integer, primary_key=True, nullable=False),
                Column('name', UnicodeText(length=None)),
                Column('data', UnicodeText(length=None)),
            )
            ''')

        # Create table in database, now model should match database.
        self._applyLatestModel()
        assertDiff(False, [], [], [])

        # Check Python code gen from database.
        diff = schemadiff.getDiffOfModelAgainstDatabase(MetaData(), self.engine, excludeTables=['migrate_version'])
        src = genmodel.ModelGenerator(diff,self.engine).genBDefinition()

        exec src in locals()

        c1 = Table('tmp_schemadiff', self.meta, autoload=True).c
        c2 = tmp_schemadiff.c
        self.compare_columns_equal(c1, c2, ['type'])
        # TODO: get rid of ignoring type

        if not self.engine.name == 'oracle':
            # Add data, later we'll make sure it's still present.
            result = self.engine.execute(self.table.insert(), id=1, name=u'mydata')
            if SQLA_06:
                dataId = result.inserted_primary_key[0]
            else:
                dataId = result.last_inserted_ids()[0]

        # Modify table in model (by removing it and adding it back to model)
        # Drop column data, add columns data2 and data3.
        self.meta.remove(self.table)
        self.table = Table(self.table_name,self.meta,
            Column('id',Integer(),primary_key=True),
            Column('name',UnicodeText(length=None)),
            Column('data2',Integer(),nullable=True),
            Column('data3',Integer(),nullable=True),
        )
        assertDiff(True, [], [], [self.table_name])

        # Apply latest model changes and find no more diffs.
        self._applyLatestModel()
        assertDiff(False, [], [], [])

        # Drop column data3, add data4
        self.meta.remove(self.table)
        self.table = Table(self.table_name,self.meta,
            Column('id',Integer(),primary_key=True),
            Column('name',UnicodeText(length=None)),
            Column('data2',Integer(),nullable=True),
            Column('data4',Float(),nullable=True),
        )
        assertDiff(True, [], [], [self.table_name])

        diff = schemadiff.getDiffOfModelAgainstDatabase(
            self.meta, self.engine, excludeTables=['migrate_version'])
        decls, upgradeCommands, downgradeCommands = genmodel.ModelGenerator(diff,self.engine).genB2AMigration(indent='')

        # decls have changed since genBDefinition
        exec decls in locals()
        # migration commands expect a namespace containing migrate_engine
        migrate_engine = self.engine
        # run the migration up and down
        exec upgradeCommands in locals()
        assertDiff(False, [], [], [])

        exec decls in locals()
        exec downgradeCommands in locals()
        assertDiff(True, [], [], [self.table_name])

        exec decls in locals()
        exec upgradeCommands in locals()
        assertDiff(False, [], [], [])

        if not self.engine.name == 'oracle':
            # Make sure data is still present.
            result = self.engine.execute(self.table.select(self.table.c.id==dataId))
            rows = result.fetchall()
            eq_(len(rows), 1)
            eq_(rows[0].name, 'mydata')

            # Add data, later we'll make sure it's still present.
            result = self.engine.execute(self.table.insert(), id=2, name=u'mydata2', data2=123)
            if SQLA_06:
                dataId2 = result.inserted_primary_key[0]
            else:
                dataId2 = result.last_inserted_ids()[0]

        # Change column type in model.
        self.meta.remove(self.table)
        self.table = Table(self.table_name,self.meta,
            Column('id',Integer(),primary_key=True),
            Column('name',UnicodeText(length=None)),
            Column('data2',String(255),nullable=True),
        )

        # XXX test type diff
        return

        assertDiff(True, [], [], [self.table_name])

        # Apply latest model changes and find no more diffs.
        self._applyLatestModel()
        assertDiff(False, [], [], [])

        if not self.engine.name == 'oracle':
            # Make sure data is still present.
            result = self.engine.execute(self.table.select(self.table.c.id==dataId2))
            rows = result.fetchall()
            self.assertEquals(len(rows), 1)
            self.assertEquals(rows[0].name, 'mydata2')
            self.assertEquals(rows[0].data2, '123')

            # Delete data, since we're about to make a required column.
            # Not even using sqlalchemy.PassiveDefault helps because we're doing explicit column select.
            self.engine.execute(self.table.delete(), id=dataId)

        if not self.engine.name == 'firebird':
            # Change column nullable in model.
            self.meta.remove(self.table)
            self.table = Table(self.table_name,self.meta,
                Column('id',Integer(),primary_key=True),
                Column('name',UnicodeText(length=None)),
                Column('data2',String(255),nullable=False),
            )
            assertDiff(True, [], [], [self.table_name])  # TODO test nullable diff

            # Apply latest model changes and find no more diffs.
            self._applyLatestModel()
            assertDiff(False, [], [], [])

            # Remove table from model.
            self.meta.remove(self.table)
            assertDiff(True, [], [self.table_name], [])
