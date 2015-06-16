from .support import (BaseWebTest, unittest, MINIMALIST_BUCKET,
                      MINIMALIST_GROUP)


class GroupViewTest(BaseWebTest, unittest.TestCase):

    collection_url = '/buckets/beers/groups'
    record_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        super(GroupViewTest, self).setUp()
        self.app.put_json('/buckets/beers', MINIMALIST_BUCKET,
                          headers=self.headers)
        resp = self.app.put_json(self.record_url,
                                 MINIMALIST_GROUP,
                                 headers=self.headers)
        self.record = resp.json['data']

    def test_collection_endpoint_lists_them_all(self):
        resp = self.app.get(self.collection_url, headers=self.headers)
        records = resp.json['data']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['members'], ['fxa:user'])

    def test_groups_can_be_posted_without_id(self):
        resp = self.app.post_json(self.collection_url,
                                  MINIMALIST_GROUP,
                                  headers=self.headers,
                                  status=201)
        self.assertIn('id', resp.json['data'])
        self.assertEqual(resp.json['data']['members'], ['fxa:user'])

    def test_groups_can_be_put_with_simple_name(self):
        self.assertEqual(self.record['id'], 'moderators')

    def test_groups_name_should_be_simple(self):
        self.app.put_json('/buckets/beers/groups/__moderator__',
                          MINIMALIST_GROUP,
                          headers=self.headers,
                          status=400)

    def test_unknown_bucket_raises_403(self):
        other_bucket = self.collection_url.replace('beers', 'sodas')
        self.app.get(other_bucket, headers=self.headers, status=403)

    def test_groups_are_isolated_by_bucket(self):
        other_bucket = self.record_url.replace('beers', 'sodas')
        self.app.put_json('/buckets/sodas',
                          MINIMALIST_BUCKET,
                          headers=self.headers)
        self.app.get(other_bucket, headers=self.headers, status=404)


class GroupManagementTest(BaseWebTest, unittest.TestCase):

    group_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        super(GroupManagementTest, self).setUp()
        self.create_bucket('beers')

    def test_groups_can_be_deleted(self):
        self.create_group('beers', 'moderators')
        self.app.delete(self.group_url, headers=self.headers)
        self.app.get(self.group_url, headers=self.headers,
                     status=404)

    def test_group_is_removed_from_users_on_group_deletion(self):
        self.app.put_json(self.group_url, MINIMALIST_GROUP,
                          headers=self.headers, status=201)
        self.assertIn(self.group_url,
                      self.permission.user_principals('fxa:user'))
        self.app.delete(self.group_url, headers=self.headers, status=200)
        self.assertNotIn(self.group_url,
                         self.permission.user_principals('fxa:user'))

    def test_group_is_removed_from_users_on_all_groups_deletion(self):
        self.create_group('beers', 'moderators', ['natim', 'fxa:user'])
        self.create_group('beers', 'reviewers', ['natim', 'alexis'])

        self.app.delete('/buckets/beers/groups', headers=self.headers,
                        status=200)

        self.assertEquals(self.permission.user_principals('fxa:user'), set())
        self.assertEquals(self.permission.user_principals('natim'), set())
        self.assertEquals(self.permission.user_principals('alexis'), set())

    def test_group_is_added_to_user_when_added_to_members(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])

        group = self.app.get('/buckets/beers/groups', headers=self.headers,
                             status=200).json['data'][0]
        self.assertIn('natim', group['members'])
        self.assertIn('mat', group['members'])

    def test_group_is_added_to_user_when_added_to_members_using_patch(self):
        self.create_group('beers', 'moderators', ['natim', 'mat'])
        group_url = '/buckets/beers/groups/moderators'
        group = {'data': {'members': ['natim', 'mat', 'alice']}}
        self.app.patch_json(group_url, group,
                            headers=self.headers, status=200)
        group = self.app.get('/buckets/beers/groups', headers=self.headers,
                             status=200).json['data'][0]
        self.assertIn('natim', group['members'])
        self.assertIn('mat', group['members'])
        self.assertIn('alice', group['members'])


class InvalidGroupTest(BaseWebTest, unittest.TestCase):

    group_url = '/buckets/beers/groups/moderators'

    def setUp(self):
        super(InvalidGroupTest, self).setUp()
        self.create_bucket('beers')

    def test_groups_must_have_members_attribute(self):
        invalid = {}
        self.app.put_json(self.group_url,
                          invalid,
                          headers=self.headers,
                          status=400)