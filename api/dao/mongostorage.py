# @author:  Renzo Frigato

import bson.objectid
import copy
import logging
import re

log = logging.getLogger('scitran.api')


class ListStorage(object):
    """
    This class provides access to sublists of a mongodb collections elements (called containers).
    """

    def __init__(self, coll_name, list_name, use_oid = False, key_fields = None):
        self.coll_name = coll_name
        self.list_name = list_name
        self.use_oid = use_oid
        self.key_fields = key_fields
        # the collection is not loaded when the class is instantiated
        # this allows to instantiate the class when the db is not available
        # and load the collection later when the db is available
        self.dbc = None

    def get_container(self, _id):
        """
        Load a container from the _id.

        This method is usually used to to check permission properties of the container.
        e.g. list of users that can access the container

        For simplicity we load its full content.
        """
        if self.dbc is None:
            raise RuntimeError('collection not initialized before calling get_container')
        if self.use_oid:
            _id = bson.objectid.ObjectId(_id)
        query = {'_id': _id}
        log.debug('query {}'.format(query))
        return self.dbc.find_one(query)

    def exec_op(self, action, _id, query_params=None, payload=None):
        """
        Generic method to execdd an operation.
        The request is dispatched to the corresponding private methods.
        """
        if self.use_oid:
            _id = bson.objectid.ObjectId(_id)
        if action == 'GET':
            return self._get_el(_id, query_params)
        if action == 'DELETE':
            return self._delete_el(_id, query_params)
        if action == 'PUT':
            return self._update_el(_id, query_params, payload)
        if action == 'POST':
            return self._create_el(_id, payload)
        raise ValueError('action should be one of GET, POST, PUT, DELETE')

    def _create_el(self, _id, payload):
        log.debug('payload {}'.format(payload))
        query = {'_id': _id }
        if self.key_fields:
            try:
                query_params = {
                    k: payload[k] for k in self.key_fields
                }
            except KeyError:
                self.abort(400, 'missing key for list {}'.format(self.list_name))
            query[self.list_name] = {'$not': {'$elemMatch': query_params} }
        update = {'$push': {self.list_name: payload} }
        log.debug('query {}'.format(query))
        log.debug('update {}'.format(update))
        return self.dbc.update_one(query, update)

    def _update_el(self, _id, query_params, payload):
        log.debug('query_params {}'.format(query_params))
        log.debug('payload {}'.format(payload))
        mod_elem = {}
        for k,v in payload.items():
            mod_elem[self.list_name + '.$.' + k] = v
        query = {'_id': _id }
        if self.key_fields:
            _eqp = {}
            exclude_query_params = None
            for k in self.key_fields:
                if query_params.get(k) is None:
                    self.abort(400, 'missing key {} in query params for list {}'.format(k, self.list_name))
                value_p = payload.get(k)
                if value_p and value_p != query_params.get(k):
                    _eqp[k] = value_p
                    exclude_query_params = _eqp
                else:
                    _eqp[k] = query_params.get(k)
        if exclude_query_params is None:
            query[self.list_name] = {'$elemMatch': query_params}
        else:
            query['$and'] = [
                {self.list_name: {'$elemMatch': query_params}},
                {self.list_name: {'$not': {'$elemMatch': exclude_query_params} }}
            ]
        update = {
            '$set': mod_elem
        }
        log.debug('query {}'.format(query))
        log.debug('update {}'.format(update))
        return self.dbc.update_one(query, update)

    def _delete_el(self, _id, query_params):
        log.debug('query_params {}'.format(query_params))
        if self.key_fields:
            for k in self.key_fields:
                if query_params.get(k) is None:
                    self.abort(400, 'missing key {} in query params for list {}'.format(k, self.list_name))
        query = {'_id': _id}
        update = {'$pull': {self.list_name: query_params} }
        log.debug('query {}'.format(query))
        log.debug('update {}'.format(update))
        return self.dbc.update_one(query, update)

    def _get_el(self, _id, query_params):
        log.debug('query_params {}'.format(query_params))
        if self.key_fields:
            for k in self.key_fields:
                if query_params.get(k) is None:
                    self.abort(400, 'missing key {} in query params for list {}'.format(k, self.list_name))
        query = {'_id': _id, self.list_name: {'$elemMatch': query_params}}
        projection = {self.list_name + '.$': 1}
        log.debug('query {}'.format(query))
        log.debug('projection {}'.format(projection))
        result = self.dbc.find_one(query, projection)
        if result and result.get(self.list_name):
            return result.get(self.list_name)[0]


class StringListStorage(ListStorage):

    def exec_op(self, action, _id, query_params=None, payload=None):
        """
        This method "flattens" the query parameter and the payload to handle string lists
        """
        if query_params is not None:
            query_params = query_params['value']
        if payload is not None:
            payload = payload.get('value')
            if payload is None:
                self.abort(400, 'Key "value" should be defined')
        return super(StringListStorage, self).exec_op(action, _id, query_params, payload)

    def _create_el(self, _id, payload):
        log.debug('payload {}'.format(payload))
        query = {'_id': _id, self.list_name: {'$ne': payload}}
        update = {'$push': {self.list_name: payload}}
        log.debug('query {}'.format(query))
        log.debug('update {}'.format(update))
        return self.dbc.update_one(query, update)

    def _update_el(self, _id, query_params, payload):
        log.debug('query_params {}'.format(payload))
        log.debug('payload {}'.format(query_params))
        query = {
            '_id': _id,
            '$and':[
                {self.list_name: query_params},
                {self.list_name: {'$ne': payload} }
            ]
        }
        update = {'$set': {self.list_name + '.$': payload}}
        log.debug('query {}'.format(query))
        log.debug('update {}'.format(update))
        return self.dbc.update_one(query, update)

    def _get_el(self, _id, query_params):
        log.debug('query_params {}'.format(query_params))
        query = {'_id': _id, self.list_name: query_params}
        projection = {self.list_name + '.$': 1}
        log.debug('query {}'.format(query))
        log.debug('projection {}'.format(projection))
        result = self.dbc.find_one(query, projection)
        if result and result.get(self.list_name):
            return result.get(self.list_name)[0]