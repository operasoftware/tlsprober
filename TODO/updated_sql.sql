# This file is used to keep database updates while changing 
# the database tables in a test database

#BEGIN;
#ALTER TABLE  "bar"
#	ADD "foo" boolean NOT NULL DEFAULT FALSE
#;	
#ALTER TABLE "bar" 
#	DROP CONSTRAINT "foo1",
#	DROP COLUMN "foo2"
#;
#select (id, foo) from bar where id=10000;
#Rollback;

BEGIN;

ROLLBACK;
