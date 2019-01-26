# Copyright 2018 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.
#

import os
import logging
import mock

from shotgun_api3.lib import mockgun

from test_base import TestBase
from mock_jira import MockedJira
from mock_jira import JIRA_PROJECT_KEY, JIRA_PROJECT, JIRA_USER, JIRA_USER_2
import sg_jira
from sg_jira.constants import SHOTGUN_JIRA_ID_FIELD

# A list of Shotgun Projects
SG_PROJECTS = [
    {"id": 1, "name": "No Sync", "type": "Project"},
    {"id": 2, "name": "Sync", "type": "Project", SHOTGUN_JIRA_ID_FIELD: JIRA_PROJECT_KEY}
]

# A list of Shotgun Tasks
SG_TASKS = [
    {
        "type": "Task",
        "id": 1,
        "content": "Task One/1",
        "task_assignees": [],
        "project": SG_PROJECTS[0]
    },
    {
        "type": "Task",
        "id": 2,
        "content": "Task One/2",
        "task_assignees": [],
        "project": SG_PROJECTS[1]
    },
]
# Faked SG event meta data
SG_EVENT_META = {
    "attribute_name": "sg_status_list",
    "entity_id": 11793,
    "entity_type": "Task",
    "field_data_type": "status_list",
    "new_value": "wtg",
    "old_value": "fin",
    "type": "attribute_change"
}

JIRA_SUMMARY_CHANGE = {
    "field": "summary",
    "fieldId": "summary",
    "fieldtype": "jira",
    "from": None,
    "fromString": "foo ba",
    "to": None,
    "toString": "foo bar"
}

JIRA_ISSUE_FIELDS = {
    "assignee": JIRA_USER,
    "attachment": [],
    "components": [],
    "created": "2018-12-18T06:15:05.626-0500",
    "creator": {
        "accountId": "557058:aecf5cfd-e13d-45a4-8db5-59da3ad254ce",
        "active": True,
        "displayName": "Sync Sync",
        "emailAddress": "syncsync@blah.com",
        "key": "syncsync",
        "name": "syncsync",
        "self": "https://myjira.atlassian.net/rest/api/2/user?accountId=123456%3Aaecf5cfd-e13d-abcdef",
        "timeZone": "America/New_York"
    },
    "customfield_11501": "11794",
    "customfield_11502": "Task",
    "description": "Task (11794)",
    "duedate": None,
    "environment": None,
    "fixVersions": [],
    "issuelinks": [],
    "issuetype": {
        "avatarId": 10318,
        "description": "A task that needs to be done.",
        "iconUrl": "https://myjira.atlassian.net/secure/viewavatar?size=xsmall&avatarId=10318&avatarType=issuetype",
        "id": "10000",
        "name": "Task",
        "self": "https://myjira.atlassian.net/rest/api/2/issuetype/10000",
        "subtask": False
    },
    "labels": [],
    "lastViewed": "2018-12-18T09:44:27.653-0500",
    "priority": {
        "iconUrl": "https://myjira.atlassian.net/images/icons/priorities/medium.svg",
        "id": "3",
        "name": "Medium",
        "self": "https://myjira.atlassian.net/rest/api/2/priority/3"
    },
    "project": JIRA_PROJECT,
    "reporter": {
        "accountId": "557058:aecf5cfd-e13d-45a4-8db5-59da3ad254ce",
        "active": True,
        "displayName": "Shotgun Synch",
        "emailAddress": "stephane.deverly@shotgunsoftware.com",
        "key": "shotgun-synch",
        "name": "shotgun-synch",
        "self": "https://myjira.atlassian.net/rest/api/2/user?accountId=557058%3Aaecf5cfd-e13d-45a4-8db5-59da3ad254ce",
        "timeZone": "America/New_York"
    },
    "resolution": None,
    "resolutiondate": None,
    "security": None,
    "status": {
        "description": "",
        "iconUrl": "https://myjira.atlassian.net/",
        "id": "10204",
        "name": "Backlog",
        "self": "https://myjira.atlassian.net/rest/api/2/status/10204",
        "statusCategory": {
            "colorName": "blue-gray",
            "id": 2,
            "key": "new",
            "name": "New",
            "self": "https://myjira.atlassian.net/rest/api/2/statuscategory/2"
        }
    },
    "subtasks": [],
    "summary": "foo bar",
    "updated": "2018-12-18T09:44:27.572-0500",
    "versions": [],
    "votes": {
        "hasVoted": False,
        "self": "https://myjira.atlassian.net/rest/api/2/issue/ST3-4/votes",
        "votes": 0
    },
    "watches": {
        "isWatching": False,
        "self": "https://myjira.atlassian.net/rest/api/2/issue/ST3-4/watchers",
        "watchCount": 1
    },
    "workratio": -1
}

JIRA_EVENT = {
    "changelog": {
        "id": "123456",
        "items": [JIRA_SUMMARY_CHANGE]
    },
    "issue": {
        "fields": JIRA_ISSUE_FIELDS,
        "id": "16642",
        "key": "ST3-4",
        "self": "https://myjira.atlassian.net/rest/api/2/issue/16642"
    },
    "issue_event_type_name": "issue_updated",
    "timestamp": 1545144267596,
    "user": {
        "accountId": "5b2be739a85c485354681b3b",
        "active": True,
        "displayName": "Marvin Paranoid",
        "emailAddress": "mparanoid@weefree.com",
        "key": "marvin.paranoid",
        "name": "marvin.paranoid",
        "self": "https://myjira.atlassian.net/rest/api/2/user?accountId=5b2be739abcdef",
        "timeZone": "Europe/Paris"
    },
    "webhookEvent": "jira:issue_updated"
}


class ExtMockgun(mockgun.Shotgun):
    """
    Add missing mocked methods to mockgun.Shotgun
    """
    def add_user_agent(*args, **kwargs):
        pass

    def set_session_uuid(*args, **kwargs):
        pass


# Mock Shotgun with mockgun, this works only if the code uses shotgun_api3.Shotgun
# and does not `from shotgun_api3 import Shotgun` and then `sg = Shotgun(...)`
@mock.patch("shotgun_api3.Shotgun")
# Mock Jira with MockedJira, this works only if the code uses jira.client.JIRA
# and does not use `from jira import JIRA` and then `jira_handle = JIRA(...)`
@mock.patch("jira.client.JIRA")
class TestJiraSyncer(TestBase):
    """
    Test syncing from Shotgun to Jira.
    """
    def _get_mocked_sg_handle(self):
        """
        Return a mocked SG handle.
        """
        return ExtMockgun(
            "https://mocked.my.com",
            "Ford Prefect",
            "xxxxxxxxxx",
        )

    def _get_syncer(self, mocked_jira, mocked_sg, name="task_issue"):
        """
        Helper to get a syncer and a bridge with a mocked Shotgun.

        :param mocked_jira: Mocked jira.client.JIRA.
        :param mocked_sg: Mocked shotgun_api3.Shotgun.
        :parma str name: A syncer name.
        """
        mocked_jira.return_value = MockedJira()
        mocked_sg.return_value = self._get_mocked_sg_handle()
        bridge = sg_jira.Bridge.get_bridge(
            os.path.join(self._fixtures_path, "settings.py")
        )
        syncer = bridge.get_syncer(name)
        if syncer:
            syncer._logger.setLevel(logging.DEBUG)
        return syncer, bridge

    def setUp(self):
        """
        Test setup.
        """
        super(TestJiraSyncer, self).setUp()
        self.set_sg_mock_schema(os.path.join(
            os.path.dirname(__file__),
            "fixtures", "schemas", "sg-jira",
        ))

    def test_bad_syncer(self, mocked_jira, mocked_sg):
        """
        Test we handle problems gracefully and that syncers settings are
        correctly handled.
        """
        # Bad setup should raise an exception
        self.assertRaisesRegexp(
            RuntimeError,
            "Sorry, I'm bad!",
            self._get_syncer,
            mocked_jira,
            mocked_sg,
            "bad_setup"
        )

        bridge = sg_jira.Bridge.get_bridge(
            os.path.join(self._fixtures_path, "settings.py")
        )
        self.assertRaisesRegexp(
            RuntimeError,
            "Sorry, I'm bad!",
            bridge.sync_in_jira,
            "bad_sg_accept",
            "Task",
            123,
            {
                "user": bridge.current_shotgun_user,
                "project": {"type": "Project", "id": 1},
                "meta": SG_EVENT_META
            }
        )
        self.assertRaisesRegexp(
            RuntimeError,
            "Sorry, I'm bad!",
            bridge.sync_in_jira,
            "bad_sg_sync",
            "Task",
            123,
            {
                "user": bridge.current_shotgun_user,
                "project": {"type": "Project", "id": 1},
                "meta": SG_EVENT_META
            }
        )

    @mock.patch(
        "sg_jira.Bridge.current_shotgun_user",
        new_callable=mock.PropertyMock
    )
    def test_shotgun_event_accept(self, mocked_cur_user, mocked_jira, mocked_sg):
        """
        Test syncer accepts the right Shotgun events.
        """
        mocked_cur_user.return_value = {"type": "ApiUser", "id": 1}
        syncer, bridge = self._get_syncer(mocked_jira, mocked_sg)
        # Empty events should be rejected
        self.assertFalse(
            syncer.accept_shotgun_event(
                "Task",
                123,
                event={}
            )
        )
        # Events without a Project should be rejected
        self.assertFalse(
            syncer.accept_shotgun_event(
                "Task",
                123,
                event={
                    "meta": SG_EVENT_META
                }
            )
        )
        # Events with a Project and a different user than the one used by
        # the bridge for Shotgun connection should be accepted
        self.assertTrue(
            syncer.accept_shotgun_event(
                "Task",
                123,
                event={
                    "project": {"type": "Project", "id": 1},
                    "user": {"type": "HumanUser", "id": 1},
                    "meta": SG_EVENT_META
                }
            )
        )
        # Events generated by ourself should be rejected
        self.assertFalse(
            syncer.accept_shotgun_event(
                "Task",
                123,
                event={
                    "user": bridge.current_shotgun_user,
                    "project": {"type": "Project", "id": 1},
                    "meta": SG_EVENT_META
                }
            )
        )
        # Task <-> Issue syncer should only accept Tasks
        self.assertFalse(
            syncer.accept_shotgun_event(
                "Ticket",
                123,
                event={
                    "user": {"type": "HumanUser", "id": 1},
                    "project": {"type": "Project", "id": 1},
                    "meta": SG_EVENT_META
                }
            )
        )

    def test_jira_event_accept(self, mocked_jira, mocked_sg):
        """
        Test syncer accepts the right Jira events.
        """
        syncer, bridge = self._get_syncer(mocked_jira, mocked_sg)
        # Check an empty event does not cause problems
        self.assertFalse(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event={}
            )
        )
        # Check a valid event is accepted
        self.assertTrue(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event=JIRA_EVENT
            )
        )

        # Events without a webhookEvent key should be rejected
        event = dict(JIRA_EVENT)
        del event["webhookEvent"]
        self.assertFalse(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event=event
            )
        )
        # We support only a couple of webhook events.
        event = dict(JIRA_EVENT)
        event["webhookEvent"] = "this is not valid"
        self.assertFalse(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event=event
            )
        )
        # A changelog is needed
        event = dict(JIRA_EVENT)
        del event["changelog"]
        self.assertFalse(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event=event
            )
        )
        # Events triggered by the syncer should be ignored
        event = dict(JIRA_EVENT)
        event["user"] = {
            "accountId": "5b2be739a85c485354681b3b",
            "active": True,
            "emailAddress": "foo@blah.com",
            "key": bridge.current_jira_username,
            "name": bridge.current_jira_username,
        }
        self.assertFalse(
            syncer.accept_jira_event(
                "Issue",
                "FAKED-001",
                event=event
            )
        )

    def test_project_match(self, mocked_jira, mocked_sg):
        """
        Test matching a Project between Shotgun and Jira, handling Jira
        create meta data and creating an Issue.
        """
        syncer, bridge = self._get_syncer(mocked_jira, mocked_sg)
        self.add_to_sg_mock_db(bridge.shotgun, SG_PROJECTS)
        self.add_to_sg_mock_db(bridge.shotgun, SG_TASKS)

        ret = bridge.sync_in_jira(
            "task_issue",
            "Task",
            1,
            event={
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 1},
                "meta": SG_EVENT_META
            }
        )
        self.assertFalse(ret)
        # Just make sure our faked Project does not really exist.
        self.assertFalse(syncer.get_jira_project(JIRA_PROJECT_KEY))
        # An error should be raised If the Project is linked to a bad Jira
        # Project
        self.assertRaisesRegexp(
            RuntimeError,
            "Unable to retrieve a Jira Project",
            bridge.sync_in_jira,
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": SG_EVENT_META
            }
        )
        # Faked Jira project
        bridge.jira.set_projects([JIRA_PROJECT])
        # Faked Jira create meta data with a required field with no default value.
        createmeta = {
            "projects": [
                {"issuetypes": [
                    {"fields": {"faked": {"name": "Faked", "required": True, "hasDefaultValue": False}}}
                ]}
            ]
        }
        # Test missing values in data
        with mock.patch.object(syncer.jira, "createmeta", return_value=createmeta) as m_cmeta:  # noqa
            # This should fail because of missing data for the required "Faked" field
            self.assertRaisesRegexp(
                ValueError,
                r"The following data is missing in order to create a Jira Task Issue: \['Faked'\]",
                bridge.sync_in_jira,
                "task_issue",
                "Task",
                2,
                {
                    "user": {"type": "HumanUser", "id": 1},
                    "project": {"type": "Project", "id": 2},
                    "meta": SG_EVENT_META
                }
            )
        # Test valid values in data
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": SG_EVENT_META
            }
        )

    def test_shotgun_assignee(self, mocked_jira, mocked_sg):
        """
        Test matching Shotgun assignment to Jira.
        """
        syncer, bridge = self._get_syncer(mocked_jira, mocked_sg)
        self.add_to_sg_mock_db(bridge.shotgun, SG_PROJECTS)
        self.add_to_sg_mock_db(bridge.shotgun, SG_TASKS)
        self.add_to_sg_mock_db(bridge.shotgun, {
            "status": "act",
            "valid": "valid",
            "type": "HumanUser",
            "name": "Ford Prefect",
            "id": 1,
            "email": JIRA_USER["emailAddress"]
        })
        self.add_to_sg_mock_db(bridge.shotgun, {
            "status": "act",
            "valid": "valid",
            "type": "HumanUser",
            "name": "Sync sync",
            "id": 2,
            "email": JIRA_USER_2["emailAddress"]
        })
        bridge.jira.set_projects([JIRA_PROJECT])
        # Remove the user used when the Issue is created
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": {
                    "entity_id": 28786,
                    "added": [],
                    "attribute_name": "task_assignees",
                    "entity_type": "Task",
                    "field_data_type": "multi_entity",
                    "removed": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 1}
                    ],
                    "type": "attribute_change",
                }
            }
        )
        task = bridge.shotgun.find_one(
            "Task",
            [["id", "is", 2]],
            [SHOTGUN_JIRA_ID_FIELD]
        )
        issue = bridge.jira.issue(task[SHOTGUN_JIRA_ID_FIELD])
        self.assertIsNone(issue.fields.assignee)
        # Add an assignee
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": {
                    "entity_id": 28786,
                    "removed": [],
                    "attribute_name": "task_assignees",
                    "entity_type": "Task",
                    "field_data_type": "multi_entity",
                    "added": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 1}
                    ],
                    "type": "attribute_change",
                }
            }
        )
        self.assertEqual(issue.fields.assignee.key, JIRA_USER["key"])
        # Replace the current assignee
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": {
                    "entity_id": 28786,
                    "removed": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 1}
                    ],
                    "attribute_name": "task_assignees",
                    "entity_type": "Task",
                    "field_data_type": "multi_entity",
                    "added": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 2}
                    ],
                    "type": "attribute_change",
                }
            }
        )
        self.assertEqual(issue.fields.assignee.key, JIRA_USER_2["key"])
        # Change the Issue assignee
        issue.update(fields={"assignee": JIRA_USER})
        self.assertEqual(issue.fields.assignee.key, JIRA_USER["key"])
        # An update with another assignee shouldn't remove the value
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": {
                    "entity_id": 28786,
                    "removed": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 2}
                    ],
                    "attribute_name": "task_assignees",
                    "entity_type": "Task",
                    "field_data_type": "multi_entity",
                    "added": [
                    ],
                    "type": "attribute_change",
                }
            }
        )
        self.assertEqual(issue.fields.assignee.key, JIRA_USER["key"])
        # An update with the assignee should remove the value
        bridge.sync_in_jira(
            "task_issue",
            "Task",
            2,
            {
                "user": {"type": "HumanUser", "id": 1},
                "project": {"type": "Project", "id": 2},
                "meta": {
                    "entity_id": 28786,
                    "removed": [
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 2},
                        {"status": "act", "valid": "valid", "type": "HumanUser", "id": 1},
                    ],
                    "attribute_name": "task_assignees",
                    "entity_type": "Task",
                    "field_data_type": "multi_entity",
                    "added": [
                    ],
                    "type": "attribute_change",
                }
            }
        )
        self.assertIsNone(issue.fields.assignee)

    def test_jira_2_shotgun(self, mocked_jira, mocked_sg):
        """
        Test syncing from Jira to Shotgun
        """
        syncer, bridge = self._get_syncer(mocked_jira, mocked_sg)
        # Syncing without the target entities shouldn't cause problems
        sg_entity_id = int(JIRA_EVENT["issue"]["fields"]["customfield_11501"])
        sg_entity_type = JIRA_EVENT["issue"]["fields"]["customfield_11502"]
        self.assertEqual(
            [],
            bridge.shotgun.find(sg_entity_type, [["id", "is", sg_entity_id]])
        )
        self.assertFalse(
            bridge.sync_in_shotgun(
                "task_issue",
                "Issue",
                "FAKED-01",
                JIRA_EVENT,
            )
        )
        # No new entity should be created
        self.assertEqual(
            [],
            bridge.shotgun.find(sg_entity_type, [["id", "is", sg_entity_id]])
        )
        self.add_to_sg_mock_db(bridge.shotgun, SG_PROJECTS)
        self.add_to_sg_mock_db(
            bridge.shotgun, {
                "type": sg_entity_type,
                "id": sg_entity_id,
                "content": "%s (%d)" % (sg_entity_type, sg_entity_id),
                "task_assignees": [],
                "project": SG_PROJECTS[0]
            }
        )
        self.assertTrue(
            bridge.sync_in_shotgun(
                "task_issue",
                "Issue",
                "FAKED-01",
                JIRA_EVENT,
            )
        )
