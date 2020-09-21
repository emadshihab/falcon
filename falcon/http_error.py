# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTPError exception class."""

from collections import OrderedDict
import xml.etree.ElementTree as et

from falcon.util import json, uri


class HTTPError(Exception):
    """Represents a generic HTTP error.

    Raise an instance or subclass of ``HTTPError`` to have Falcon return
    a formatted error response and an appropriate HTTP status code
    to the client when something goes wrong. JSON and XML media types
    are supported by default.

    To customize the error presentation, implement a custom error
    serializer and set it on the :class:`~.App` instance via
    :meth:`~.App.set_error_serializer`.

    To customize what data is passed to the serializer, subclass
    ``HTTPError`` and override the ``to_dict()`` method (``to_json()``
    is implemented via ``to_dict()``). To also support XML, override
    the ``to_xml()`` method.

    Args:
        status (str): HTTP status code and text, such as "400 Bad Request"

    Keyword Args:
        title (str): Human-friendly error title. If not provided, defaults
            to the HTTP status line as determined by the ``status`` argument.
        description (str): Human-friendly description of the error, along with
            a helpful suggestion or two (default ``None``).
        headers (dict or list): A ``dict`` of header names and values
            to set, or a ``list`` of (*name*, *value*) tuples. Both *name* and
            *value* must be of type ``str`` or ``StringType``, and only
            character values 0x00 through 0xFF may be used on platforms that
            use wide characters.

            Note:
                The Content-Type header, if present, will be overridden. If
                you wish to return custom error messages, you can create
                your own HTTP error class, and install an error handler
                to convert it into an appropriate HTTP response for the
                client

            Note:
                Falcon can process a list of ``tuple`` slightly faster
                than a ``dict``.

        href (str): A URL someone can visit to find out more information
            (default ``None``). Unicode characters are percent-encoded.
        href_text (str): If href is given, use this as the friendly
            title/description for the link (default 'App documentation
            for this error').
        code (int): An internal code that customers can reference in their
            support request or to help them when searching for knowledge
            base articles related to this error (default ``None``).

    Attributes:
        status (str): HTTP status line, e.g. '748 Confounded by Ponies'.
        has_representation (bool): Read-only property that determines
            whether error details will be serialized when composing
            the HTTP response. In ``HTTPError`` this property always
            returns ``True``, but child classes may override it
            in order to return ``False`` when an empty HTTP body is desired.

            (See also: :class:`falcon.http_error.NoRepresentation`)

            Note:
                A custom error serializer
                (see :meth:`~.App.set_error_serializer`) may choose to set a
                response body regardless of the value of this property.

        title (str): Error title to send to the client.
        description (str): Description of the error to send to the client.
        headers (dict): Extra headers to add to the response.
        link (str): An href that the client can provide to the user for
            getting help.
        code (int): An internal application code that a user can reference when
            requesting support for the error.
    """

    __slots__ = (
        'status',
        'title',
        'description',
        'headers',
        'link',
        'code',
    )

    def __init__(self, status, title=None, description=None, headers=None,
                 href=None, href_text=None, code=None):
        self.status = status

        # TODO(kgriffs): HTTP/2 does away with the "reason phrase". Eventually
        #   we'll probably switch over to making everything code-based to more
        #   easily support HTTP/2. When that happens, should we continue to
        #   include the reason phrase in the title?
        self.title = title or status

        self.description = description
        self.headers = headers
        self.code = code

        if href:
            link = self.link = OrderedDict()
            link['text'] = (href_text or 'Documentation related to this error')
            link['href'] = uri.encode(href)
            link['rel'] = 'help'
        else:
            self.link = None

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.status)

    @property
    def has_representation(self):
        return True

    def to_dict(self, obj_type=dict):
        """Return a basic dictionary representing the error.

        This method can be useful when serializing the error to hash-like
        media types, such as YAML, JSON, and MessagePack.

        Args:
            obj_type: A dict-like type that will be used to store the
                error information (default ``dict``).

        Returns:
            dict: A dictionary populated with the error's title,
            description, etc.

        """

        obj = obj_type()

        obj['title'] = self.title

        if self.description is not None:
            obj['description'] = self.description

        if self.code is not None:
            obj['code'] = self.code

        if self.link is not None:
            obj['link'] = self.link

        return obj

    def to_json(self):
        """Return a pretty-printed JSON representation of the error.

        Returns:
            str: A JSON document for the error.

        """

        obj = self.to_dict(OrderedDict)
        return json.dumps(obj, ensure_ascii=False)

    def to_xml(self):
        """Return an XML-encoded representation of the error.

        Returns:
            str: An XML document for the error.

        """

        error_element = et.Element('error')

        et.SubElement(error_element, 'title').text = self.title

        if self.description is not None:
            et.SubElement(error_element, 'description').text = self.description

        if self.code is not None:
            et.SubElement(error_element, 'code').text = str(self.code)

        if self.link is not None:
            link_element = et.SubElement(error_element, 'link')

            for key in ('text', 'href', 'rel'):
                et.SubElement(link_element, key).text = self.link[key]

        return (b'<?xml version="1.0" encoding="UTF-8"?>' +
                et.tostring(error_element, encoding='utf-8'))


class NoRepresentation:
    """Mixin for ``HTTPError`` child classes that have no representation.

    This class can be mixed in when inheriting from ``HTTPError``, in order
    to override the `has_representation` property such that it always
    returns ``False``. This, in turn, will cause Falcon to return an empty
    response body to the client.

    You can use this mixin when defining errors that either should not have
    a body (as dictated by HTTP standards or common practice), or in the
    case that a detailed error response may leak information to an attacker.

    Note:
        This mixin class must appear before ``HTTPError`` in the base class
        list when defining the child; otherwise, it will not override the
        `has_representation` property as expected.

    """

    @property
    def has_representation(self):
        return False


class OptionalRepresentation:
    """Mixin for ``HTTPError`` child classes that may have a representation.

    This class can be mixed in when inheriting from ``HTTPError`` in order
    to override the `has_representation` property, such that it will
    return ``False`` when the error instance has no description
    (i.e., the `description` kwarg was not set).

    You can use this mixin when defining errors that do not include
    a body in the HTTP response by default, serializing details only when
    the web developer provides a description of the error.

    Note:
        This mixin class must appear before ``HTTPError`` in the base class
        list when defining the child; otherwise, it will not override the
        `has_representation` property as expected.

    """
    @property
    def has_representation(self):
        return super(OptionalRepresentation, self).description is not None

        import functools
import io
import json

import pytest

import falcon
import falcon.testing as testing


def validate(req, resp, resource, params):
    assert resource
    raise falcon.HTTPBadRequest('Invalid thing', 'Your thing was not '
                                'formatted correctly.')


def validate_param(req, resp, resource, params, param_name, maxval=100):
    assert resource

    limit = req.get_param_as_int(param_name)
    if limit and int(limit) > maxval:
        msg = '{0} must be <= {1}'.format(param_name, maxval)
        raise falcon.HTTPBadRequest('Out of Range', msg)


class ResourceAwareValidateParam:
    def __call__(self, req, resp, resource, params):
        assert resource
        validate_param(req, resp, resource, params, 'limit')


def validate_field(req, resp, resource, params, field_name='test'):
    assert resource

    try:
        params[field_name] = int(params[field_name])
    except ValueError:
        raise falcon.HTTPBadRequest()


def parse_body(req, resp, resource, params):
    assert resource

    length = req.content_length or 0
    if length != 0:
        params['doc'] = json.load(io.TextIOWrapper(req.bounded_stream, 'utf-8'))


def bunnies(req, resp, resource, params):
    assert resource
    params['bunnies'] = 'fuzzy'


def frogs(req, resp, resource, params):
    assert resource

    if 'bunnies' in params:
        params['bunnies'] = 'fluffy'

    params['frogs'] = 'not fluffy'


class Fish:
    def __call__(self, req, resp, resource, params):
        assert resource
        params['fish'] = 'slippery'

    def hook(self, req, resp, resource, params):
        assert resource
        params['fish'] = 'wet'


# NOTE(kgriffs): Use partial methods for these next two in order
# to make sure we handle that correctly.
def things_in_the_head(header, value, req, resp, resource, params):
    resp.set_header(header, value)


bunnies_in_the_head = functools.partial(
    things_in_the_head,
    'X-Bunnies',
    'fluffy'
)

frogs_in_the_head = functools.partial(
    things_in_the_head,
    'X-Frogs',
    'not fluffy'
)


class WrappedRespondersResource:

    @falcon.before(validate_param, 'limit', 100)
    @falcon.before(parse_body)
    def on_get(self, req, resp, doc):
        self.req = req
        self.resp = resp
        self.doc = doc

    @falcon.before(validate)
    def on_put(self, req, resp):
        self.req = req
        self.resp = resp


class WrappedRespondersResourceChild(WrappedRespondersResource):

    @falcon.before(validate_param, 'x', maxval=1000)
    def on_get(self, req, resp):
        pass

    def on_put(self, req, resp):
        # Test passing no extra args
        super(WrappedRespondersResourceChild, self).on_put(req, resp)


@falcon.before(bunnies)
class WrappedClassResource:

    _some_fish = Fish()

    # Test non-callable should be skipped by decorator
    on_patch = {}  # type: ignore

    @falcon.before(validate_param, 'limit')
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(validate_param, 'limit')
    def on_head(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(_some_fish)
    def on_post(self, req, resp, fish, bunnies):
        self._capture(req, resp, bunnies)
        self.fish = fish

    @falcon.before(_some_fish.hook)
    def on_put(self, req, resp, fish, bunnies):
        self._capture(req, resp, bunnies)
        self.fish = fish

    def _capture(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies


# NOTE(swistakm): we use both type of hooks (class and method)
# at once for the sake of simplicity
@falcon.before(bunnies)
class ClassResourceWithAwareHooks:
    hook_as_class = ResourceAwareValidateParam()

    @falcon.before(validate_param, 'limit', 10)
    def on_get(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(validate_param, 'limit')
    def on_head(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(hook_as_class)
    def on_put(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    @falcon.before(hook_as_class.__call__)
    def on_post(self, req, resp, bunnies):
        self._capture(req, resp, bunnies)

    def _capture(self, req, resp, bunnies):
        self.req = req
        self.resp = resp
        self.bunnies = bunnies


class TestFieldResource:

    @falcon.before(validate_field, field_name='id')
    def on_get(self, req, resp, id):
        self.id = id


class TestFieldResourceChild(TestFieldResource):

    def on_get(self, req, resp, id):
        # Test passing a single extra arg
        super(TestFieldResourceChild, self).on_get(req, resp, id)


class TestFieldResourceChildToo(TestFieldResource):

    def on_get(self, req, resp, id):
        # Test passing a single kwarg, but no extra args
        super(TestFieldResourceChildToo, self).on_get(req, resp, id=id)


@falcon.before(bunnies)
@falcon.before(frogs)
@falcon.before(Fish())
@falcon.before(bunnies_in_the_head)
@falcon.before(frogs_in_the_head)
class ZooResource:

    def on_get(self, req, resp, bunnies, frogs, fish):
        self.bunnies = bunnies
        self.frogs = frogs
        self.fish = fish


class ZooResourceChild(ZooResource):

    def on_get(self, req, resp):
        super(ZooResourceChild, self).on_get(
            req,
            resp,

            # Test passing a mixture of args and kwargs
            'fluffy',
            'not fluffy',
            fish='slippery'
        )


@pytest.fixture
def wrapped_aware_resource():
    return ClassResourceWithAwareHooks()


@pytest.fixture
def wrapped_resource():
    return WrappedClassResource()


@pytest.fixture
def resource():
    return WrappedRespondersResource()


@pytest.fixture
def client(resource):
    app = falcon.App()
    app.add_route('/', resource)
    return testing.TestClient(app)


@pytest.mark.parametrize('resource', [ZooResource(), ZooResourceChild()])
def test_multiple_resource_hooks(client, resource):
    client.app.add_route('/', resource)

    result = client.simulate_get('/')

    assert 'not fluffy' == result.headers['X-Frogs']
    assert 'fluffy' == result.headers['X-Bunnies']

    assert 'fluffy' == resource.bunnies
    assert 'not fluffy' == resource.frogs
    assert 'slippery' == resource.fish


def test_input_validator(client):
    result = client.simulate_put('/')
    assert result.status_code == 400


def test_input_validator_inherited(client):
    client.app.add_route('/', WrappedRespondersResourceChild())
    result = client.simulate_put('/')
    assert result.status_code == 400

    result = client.simulate_get('/', query_string='x=1000')
    assert result.status_code == 200

    result = client.simulate_get('/', query_string='x=1001')
    assert result.status_code == 400


def test_param_validator(client):
    result = client.simulate_get('/', query_string='limit=10', body='{}')
    assert result.status_code == 200

    result = client.simulate_get('/', query_string='limit=101')
    assert result.status_code == 400


@pytest.mark.parametrize(
    'resource',
    [
        TestFieldResource(),
        TestFieldResourceChild(),
        TestFieldResourceChildToo(),
    ]
)
def test_field_validator(client, resource):
    client.app.add_route('/queue/{id}/messages', resource)
    result = client.simulate_get('/queue/10/messages')
    assert result.status_code == 200
    assert resource.id == 10

    result = client.simulate_get('/queue/bogus/messages')
    assert result.status_code == 400


def test_parser(client, resource):
    client.simulate_get('/', body=json.dumps({'animal': 'falcon'}))
    assert resource.doc == {'animal': 'falcon'}


def test_wrapped_resource(client, wrapped_resource):
    client.app.add_route('/wrapped', wrapped_resource)
    result = client.simulate_patch('/wrapped')
    assert result.status_code == 405

    result = client.simulate_get('/wrapped', query_string='limit=10')
    assert result.status_code == 200
    assert 'fuzzy' == wrapped_resource.bunnies

    result = client.simulate_head('/wrapped')
    assert result.status_code == 200
    assert 'fuzzy' == wrapped_resource.bunnies

    result = client.simulate_post('/wrapped')
    assert result.status_code == 200
    assert 'slippery' == wrapped_resource.fish

    result = client.simulate_get('/wrapped', query_string='limit=101')
    assert result.status_code == 400
    assert wrapped_resource.bunnies == 'fuzzy'


def test_wrapped_resource_with_hooks_aware_of_resource(client, wrapped_aware_resource):
    client.app.add_route('/wrapped_aware', wrapped_aware_resource)

    result = client.simulate_patch('/wrapped_aware')
    assert result.status_code == 405

    result = client.simulate_get('/wrapped_aware', query_string='limit=10')
    assert result.status_code == 200
    assert wrapped_aware_resource.bunnies == 'fuzzy'

    for method in ('HEAD', 'PUT', 'POST'):
        result = client.simulate_request(method, '/wrapped_aware')
        assert result.status_code == 200
        assert wrapped_aware_resource.bunnies == 'fuzzy'

    result = client.simulate_get('/wrapped_aware', query_string='limit=11')
    assert result.status_code == 400
    assert wrapped_aware_resource.bunnies == 'fuzzy'


_another_fish = Fish()


def header_hook(req, resp, resource, params):
    value = resp.get_header('X-Hook-Applied') or '0'
    resp.set_header('X-Hook-Applied', str(int(value) + 1))


@falcon.before(header_hook)
class PiggybackingCollection:

    def __init__(self):
        self._items = {}
        self._sequence = 0

    @falcon.before(_another_fish.hook)
    def on_delete(self, req, resp, fish, itemid):
        del self._items[itemid]
        resp.set_header('X-Fish-Trait', fish)
        resp.status = falcon.HTTP_NO_CONTENT

    @falcon.before(header_hook)
    @falcon.before(_another_fish.hook)
    @falcon.before(header_hook)
    def on_delete_collection(self, req, resp, fish):
        if fish != 'wet':
            raise falcon.HTTPUnavailableForLegalReasons('fish must be wet')
        self._items = {}
        resp.status = falcon.HTTP_NO_CONTENT

    @falcon.before(_another_fish)
    def on_get(self, req, resp, fish, itemid):
        resp.set_header('X-Fish-Trait', fish)
        resp.media = self._items[itemid]

    def on_get_collection(self, req, resp):
        resp.media = sorted(self._items.values(),
                            key=lambda item: item['itemid'])

    def on_head_(self):
        return 'I shall not be decorated.'

    def on_header(self):
        return 'I shall not be decorated.'

    def on_post_collection(self, req, resp):
        self._sequence += 1
        itemid = self._sequence
        self._items[itemid] = dict(req.media, itemid=itemid)
        resp.location = '/items/{}'.format(itemid)
        resp.status = falcon.HTTP_CREATED


@pytest.fixture
def app_client():
    items = PiggybackingCollection()

    app = falcon.App()
    app.add_route('/items', items, suffix='collection')
    app.add_route('/items/{itemid:int}', items)

    return testing.TestClient(app)


def test_piggybacking_resource_post_item(app_client):
    resp1 = app_client.simulate_post('/items', json={'color': 'green'})
    assert resp1.status_code == 201
    assert 'X-Fish-Trait' not in resp1.headers
    assert resp1.headers['Location'] == '/items/1'
    assert resp1.headers['X-Hook-Applied'] == '1'

    resp2 = app_client.simulate_get(resp1.headers['Location'])
    assert resp2.status_code == 200
    assert resp2.headers['X-Fish-Trait'] == 'slippery'
    assert resp2.headers['X-Hook-Applied'] == '1'
    assert resp2.json == {'color': 'green', 'itemid': 1}

    resp3 = app_client.simulate_get('/items')
    assert resp3.status_code == 200
    assert 'X-Fish-Trait' not in resp3.headers
    assert resp3.headers['X-Hook-Applied'] == '1'
    assert resp3.json == [{'color': 'green', 'itemid': 1}]


def test_piggybacking_resource_post_and_delete(app_client):
    for number in range(1, 8):
        resp = app_client.simulate_post('/items', json={'number': number})
        assert resp.status_code == 201
        assert resp.headers['X-Hook-Applied'] == '1'

        assert len(app_client.simulate_get('/items').json) == number

    resp = app_client.simulate_delete('/items/{}'.format(number))
    assert resp.status_code == 204
    assert resp.headers['X-Fish-Trait'] == 'wet'
    assert resp.headers['X-Hook-Applied'] == '1'
    assert len(app_client.simulate_get('/items').json) == 6

    resp = app_client.simulate_delete('/items')
    assert resp.status_code == 204
    assert resp.headers['X-Hook-Applied'] == '3'
    assert app_client.simulate_get('/items').json == []


def test_decorable_name_pattern():
    resource = PiggybackingCollection()
    assert resource.on_head_() == 'I shall not be decorated.'
    assert resource.on_header() == 'I shall not be decorated.'

