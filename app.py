#!/usr/bin/python3
from abc import ABC

import tornado.ioloop
import tornado.web
import tornado.netutil
import tornado.httpserver
import tornado.httpclient

import os
import signal
import subprocess
from datetime import datetime
import isodate

import json
from url_normalize import url_normalize

from redminelib import Redmine, exceptions as redmine_exceptions


startup_timestamp = datetime.now()


class HealthHandler(tornado.web.RequestHandler, ABC):
    # noinspection PyAttributeOutsideInit
    def initialize(self):
        self.git_version = self._load_git_version()

    @staticmethod
    def _load_git_version():
        v = None

        # try file git-version.txt first
        gitversion_file = "git-version.txt"
        if os.path.exists(gitversion_file):
            with open(gitversion_file) as f:
                v = f.readline().strip()

        # if not available, try git
        if v is None:
            try:
                v = subprocess.check_output(["git", "describe", "--always", "--dirty"],
                                            cwd=os.path.dirname(__file__)).strip().decode()
            except subprocess.CalledProcessError as e:
                print("Checking git version lead to non-null return code ", e.returncode)

        return v

    def get(self):
        health = dict()
        health['api_version'] = 'v0'

        if self.git_version is not None:
            health['git_version'] = self.git_version

        health['timestamp'] = isodate.datetime_isoformat(datetime.now())
        health['uptime'] = isodate.duration_isoformat(datetime.now() - startup_timestamp)

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(health, indent=4))
        self.set_status(200)


class Oas3Handler(tornado.web.RequestHandler, ABC):
    def get(self):
        with open('OAS3.yml', 'r') as f:
            oas3 = f.read()
            self.write(oas3)
        self.finish()


class RedmineActionablesHandler(tornado.web.RequestHandler, ABC):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

    def get(self):
        try:
            redmineurl = self.get_argument('url', None)
            if redmineurl is None or redmineurl == '':
                raise tornado.web.HTTPError(status_code=400, reason="Redmine URL must not be empty")
            apikey = self.get_argument('apikey', None)
            if apikey is None or apikey == '':
                raise tornado.web.HTTPError(status_code=400, reason="API key URL must not be empty")

            result = dict()
            issues = list()
            projects = dict()

            redmine = Redmine(redmineurl, key=apikey)

            result['redmine'] = redmineurl

            rm_user = redmine.user.get('current')
            result['user_id'] = rm_user.id

            # We cannot filter issues that are blocked, so we have to get all open issues to see
            # a) if somebody is blocking
            # b) if somebody is an open sub-issue

            # Map of all issues
            issue_all = dict()
            # Map of user issues
            issue_user = dict()
            # Map of blocked issues
            # Contains a list of blocking issues
            issue_rel_blockedby = dict()

            # Start with all issues which are still open, the rest is not relevant
            rm_issues = redmine.issue.filter(
                status_id='open',
                include=['relations']
            )

            # put into the maps
            for rm_issue in rm_issues:
                issue_all[rm_issue.id] = rm_issue
                if ('assigned_to' in dir(rm_issue)) and (rm_issue.assigned_to.id == rm_user.id):
                    issue_user[rm_issue.id] = rm_issue

            # reiterate issues
            # - remove blocked by other issues
            # - removes following other issues
            # - remove parents, because they have open issues

            for rm_issue in issue_all.values():
                # find blocked issues and remove them from the user list
                for rm_rel in rm_issue.relations:
                    if rm_rel.relation_type == 'blocks':
                        if rm_rel.issue_id in issue_all.keys():
                            if rm_rel.issue_to_id not in issue_rel_blockedby:
                                issue_rel_blockedby[rm_rel.issue_to_id] = list()
                            issue_rel_blockedby[rm_rel.issue_to_id].append(rm_issue.id)

                            # issue_user[rm_rel.issue_to_id] = None

                    if rm_rel.relation_type == 'blocked_by':
                        if rm_rel.issue_to_id in issue_all.keys():
                            if rm_issue.id not in issue_rel_blockedby:
                                issue_rel_blockedby[rm_issue.id] = list()
                            issue_rel_blockedby[rm_issue.id].append(rm_rel.issue_to_id)

                            # issue_user[rm_rel.issue_id] = None

                    if rm_rel.relation_type == 'precedes':
                        if rm_rel.issue_id in issue_all.keys():
                            issue_user[rm_rel.issue_to_id] = None

                    if rm_rel.relation_type == 'follows':
                        if rm_rel.issue_to_id in issue_all.keys():
                            issue_user[rm_rel.issue_id] = None

                if 'parent' in dict(rm_issue):
                    issue_user[rm_issue.parent.id] = None

                if 'project' in dir(rm_issue):
                    # add to projects if not already loaded
                    pr_id = rm_issue.project.id
                    if pr_id not in projects:
                        projects[pr_id] = redmine.project.get(pr_id)

                    # if project is closed -> remove issue
                    if projects[pr_id].status == 5:
                        issue_user[rm_issue.id] = None

            # pivot-date
            pd = datetime.today().date()

            # remove user issues with start date > today, if they have any
            for issue in issue_user.values():
                if issue is None:
                    continue
                if 'start_date' not in dir(issue):
                    continue

                # sometimes 'start_date' is in dir, but not accessible
                # we ignore those
                try:
                    sd = issue.start_date  # type: datetime.date

                    if sd > pd:
                        issue_user[issue.id] = None
                except redmine_exceptions.ResourceAttrError:
                    pass

            # Collect the result projects
            res_projects = dict()
            for project in projects.values():
                if project is not None:
                    # ignore closed projects
                    if project.status == 5:
                        continue

                    entry = dict()

                    # render the project's URI (with normalization)
                    uri_s = "{0}/projects/{1}".format(redmineurl, project.identifier)
                    entry['uri'] = url_normalize(uri_s)

                    entry['local_id'] = project.id

                    for key in ['identifier',
                                'name',
                                'status',
                                'description']:
                        if key in dir(project):
                            entry[key] = project.__getattr__(key)

                    res_projects[project.id] = entry

            result['projects'] = res_projects

            # Collect the result issues
            for issue in issue_user.values():
                if issue is not None:
                    entry = dict()

                    # render the issue's URI (with normalization)
                    uri_s = "{0}/issues/{1}".format(redmineurl, issue.id)
                    entry['uri'] = url_normalize(uri_s)

                    entry['local_id'] = issue.id
                    for key in ['subject',
                                'description',
                                'done_ratio']:
                        if key in dir(issue):
                            entry[key] = issue.__getattr__(key)

                    try:
                        if 'due_date' in dir(issue) and issue.due_date is not None:
                            dd = issue.due_date
                            entry['due_date'] = str(dd)
                    except redmine_exceptions.ResourceAttrError:
                        pass

                    if 'parent' in dir(issue) and issue.parent is not None:
                        entry['parent_local_id'] = issue.parent.id

                    if 'project' in dir(issue) and issue.project is not None:
                        entry['project_local_id'] = issue.project.id

                    if issue.id in issue_rel_blockedby:
                        entry['blocked_by'] = issue_rel_blockedby[issue.id]

                    issues.append(entry)
            result['issues'] = issues

            # Add list of blocked issues
            result['blocked'] = list(filter(
                lambda i: i in issue_user and issue_user[i] is not None, issue_rel_blockedby.keys()
            ))

            self.add_header("Content-Type", "application/json")
            self.write(json.dumps(result, indent=4))
            self.set_status(200)
            self.finish()

        except redmine_exceptions.AuthError as e:
            raise tornado.web.HTTPError(status_code=403, reason="{0}".format(e))


def make_app():
    version_path = r"/v[0-9]"
    return tornado.web.Application([
        (version_path + r"/health", HealthHandler),
        (version_path + r"/oas3", Oas3Handler),
        (version_path + r"/redmine/actionables", RedmineActionablesHandler)
    ])


def load_env(key, default):
    if key in os.environ:
        return os.environ[key]
    else:
        return default


signal_received = False


def main():
    arg_port = load_env('PORT', 8080)

    # Setup

    app = make_app()
    sockets = tornado.netutil.bind_sockets(arg_port, '')
    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)

    port = None

    for s in sockets:
        print('Listening on %s, port %d' % s.getsockname()[:2])
        if port is None:
            port = s.getsockname()[1]

    ioloop = tornado.ioloop.IOLoop.instance()

    def register_signal(sig, _frame):
        # noinspection PyGlobalUndefined
        global signal_received
        print("%s received, stopping server" % sig)
        server.stop()  # no more requests are accepted
        signal_received = True

    def stop_on_signal():
        # noinspection PyGlobalUndefined
        global signal_received
        if signal_received:
            ioloop.stop()
            print("IOLoop stopped")

    tornado.ioloop.PeriodicCallback(stop_on_signal, 1000).start()
    signal.signal(signal.SIGTERM, register_signal)
    print("Starting server")

    global signal_received
    while not signal_received:
        try:
            ioloop.start()
        except KeyboardInterrupt:
            print("Keyboard interrupt")
            register_signal(signal.SIGTERM, None)

    # Teardown

    print("Server stopped")


if __name__ == "__main__":
    main()
