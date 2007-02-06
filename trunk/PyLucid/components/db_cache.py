#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
PyLucid string/object database cache module

Last commit info:
----------------------------------
$LastChangedDate$
$Rev$
$Author$

Created by Jens Diemer

license:
    GNU General Public License v2 or above
    http://www.opensource.org/licenses/gpl-license.php

"""

__version__= "$Rev$"


import time

try:
    import cPickle as pickle
except ImportError:
    import pickle



class DB_Cache(object):

    def __init__(self, request, response):
        # shorthands
        self.request    = request
        self.db         = request.db
        self.session    = request.session
        self.page_msg   = response.page_msg

        #~ self.drop_table()
        #~ self.create_table()

        #~ test = {
            #~ "liste" : [1,2,3],
            #~ "tuple" : (4,5,6),
            #~ "unicode" : u"testäöüß",
        #~ }
        #~ try:
            #~ self.put_object(u"abc", 10, test)
        #~ except Exception, e:
            #~ self.page_msg(e)

        #~ self.debug()

        #~ try:
            #~ self.page_msg(self.get_object(id = u"abc"))
        #~ except Exception, e:
            #~ self.page_msg(e)


    def put_object(self, id, expiry_time, object):
        """
        Packt ein Object gepicklet in die DB
        id          - String - Zum wieder finden der Eintrags
        expiry_time - int - Haltbarkeit Zeit in Sek.
        object      - Das zu pickelnde Objekt
        """
        expiry_time = int(time.time() + expiry_time)
        object = pickle.dumps(object)

        request_ip = self.request.environ.get("REMOTE_ADDR","unknown")

        self.db.insert(
            table = "object_cache",
            data  = {
                "id"            : id,
                "expiry_time"   : expiry_time,
                "request_ip"    : request_ip,
                "user_id"       : self.session.get("user_id", None),
                "pickled_data"  : object,
            }
        )
        self.db.commit()

    def get_object(self, id):
        """
        Holt aus der DB ein gepickeltes Objekt wieder herraus.
        """
        self.delete_old_entries()

        try:
            object = self.db.select(
                select_items    = ["pickled_data"],
                from_table      = "object_cache",
                where           = ("id",id)
            )[0]["pickled_data"]
        except (IndexError, KeyError):
            raise CacheObjectNotFound(
                "Can't get cache object with id '%s' from db" % id
            )

        object = pickle.loads(str(object))
        return object

    def delete_object(self, id):
        """
        Löscht einen bestimmten Eintrag
        """
        self.db.delete(
            table   = "object_cache",
            where   = ("id", id),
            limit   = 1
        )
        self.db.commit()

    def delete_old_entries(self):
        """
        Löscht alte Einträge
        """
        SQLcommand  = "DELETE FROM $$object_cache WHERE expiry_time < %s"
        current_time = time.time()

        #~ self.debug()

        try:
            self.db.cursor.execute(SQLcommand, (current_time,))
        except Exception, e:
            self.page_msg.red("Can't delete old object cache entries: %s" % e)

        #~ self.debug()


    #_________________________________________________________________________

    def debug(self):
        self.page_msg("db_cache Debug:")
        debug_data = self.db.select(
            select_items    = ["*"],
            from_table      = "object_cache",
        )
        #~ self.page_msg(debug_data)
        for line in debug_data:
            self.page_msg(line)
        self.page_msg("---[ debug end ]---")


class CacheObjectNotFound(Exception):
    """
    Eintrag ist nicht in der DB
    """
    pass