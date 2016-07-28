# -*- coding: utf-8 -*-
from errbot import BotPlugin
from errbot import botcmd
from itertools import chain
import re

CONFIG_TEMPLATE = {'API_URL': "http://jira.example.com",
                   'USERNAME': 'errbot',
                   'PASSWORD': 'password',
                   'OAUTH_ACCESS_TOKEN': None,
                   'OAUTH_ACCESS_TOKEN_SECRET': None,
                   'OAUTH_CONSUMER_KEY': None,
                   'OAUTH_KEY_CERT_FILE': None}

try:
    from jira import JIRA, JIRAError
except ImportError:
    raise("Please install 'jira' python package")


class Jira(BotPlugin):
    """
    An errbot plugin for working with Atlassian JIRA
    """

    def configure(self, configuration):
        if configuration is not None and configuration != {}:
            config = dict(chain(CONFIG_TEMPLATE.items(),
                                configuration.items()))
        else:
            config = CONFIG_TEMPLATE
        super(Jira, self).configure(config)

    def check_configuration(self, configuration):
        # TODO(alex) do some validation here!
        pass

    def get_configuration_template(self):
        """
        Returns a template of the configuration this plugin supports
        """
        return CONFIG_TEMPLATE

    def activate(self):
        if self.config is None:
            # Do not activate the plugin until it is configured
            message = 'Jira not configured.'
            self.log.info(message)
            self.warn_admins(message)
            return

        self.jira_connect = self._login()
        if self.jira_connect:
            super().activate()
        else:
            self.log.error('Failed to activate Jira plugin, maybe check the configuration')

    def _login_oauth(self):
        """
        Login to Jira with OAUTH
        """
        api_url = self.config['API_URL']
        # TODO(alex) make this check more robust
        if self.config['OAUTH_ACCESS_TOKEN'] is None:
            message = 'oauth configuration not set'
            self.log.info(message)
            return None

        key_cert_data = None
        cert_file = self.config['OAUTH_KEY_CERT_FILE']
        try:
            with open(cert_file, 'r') as key_cert_file:
                key_cert_data = key_cert_file.read()
            oauth_dict = {
                'access_token': self.config['OAUTH_ACCESS_TOKEN'],
                'access_token_secret': self.config['OAUTH_ACCESS_TOKEN_SECRET'],
                'consumer_key': self.config['OAUTH_CONSUMER_KEY'],
                'key_cert': key_cert_data
            }
            authed_jira = JIRA(server=api_url, oauth=oauth_dict)
            self.log.info('logging into {} via oauth'.format(api_url))
            return authed_jira
        except JIRAError:
            message = 'Unable to login to {} via oauth'.format(api_url)
            self.log.error(message)
            return None
        except TypeError:
            message = 'Unable to read key file {}'.format(cert_file)
            self.log.error(message)
            return None

    def _login_basic(self):
        """
        Login to Jira with basic auth
        """
        api_url = self.config['API_URL']
        username = self.config['USERNAME']
        password = self.config['PASSWORD']
        try:
            authed_jira = JIRA(server=api_url, basic_auth=(username, password))
            self.log.info('logging into {} via basic auth'.format(api_url))
            return authed_jira
        except JIRAError:
            message = 'Unable to login to {} via basic auth'.format(api_url)
            self.log.error(message)
            return None

    def _login(self):
        """
        Login to Jira
        """
        self.jira_connect = self._login_oauth()
        if self.jira_connect is None:
            self.jira_connect = self._login_basic()
        return self.jira_connect

    def _verify_issue_id(self, msg, issue):
        if issue == '':
            self.send(msg.frm,
                      'issue id cannot be empty',
                      message_type=msg.type,
                      in_reply_to=msg,
                      groupchat_nick_reply=True)
            return ''
        matches = []
        regexes = []
        regexes.append(r'([^\W\d_]+)\-(\d+)')  # e.g.: issue-1234
        regexes.append(r'([^\W\d_]+)(\d+)')    # e.g.: issue1234
        for regex in regexes:
            matches.extend(re.findall(regex, msg.body, flags=re.I | re.U))
        if matches:
            for match in set(matches):
                return match[0].upper() + '-' + match[1]
        self.send(msg.frm,
                  'issue id format incorrect',
                  message_type=msg.type,
                  in_reply_to=msg,
                  groupchat_nick_reply=True)
        return ''

    @botcmd(split_args_with=' ')
    def jira(self, msg, args):
        """
        Returns the subject of the issue and a link to it.
        """
        issue = self._verify_issue_id(msg, args.pop(0))
        if issue is '':
            return
        jira = self.jira_connect
        try:
            issue = jira.issue(issue)
            response = '({4}) "{0}" (by {2})\nassigned to {1} - {3}'.format(
                issue.fields.summary,
                issue.fields.assignee.displayName,
                issue.fields.reporter.displayName,
                issue.permalink(),
                issue.fields.status.name
            )
        except JIRAError:
            response = 'issue {0} not found.'.format(issue)
        self.send(msg.frm,
                  response,
                  message_type=msg.type,
                  in_reply_to=msg,
                  groupchat_nick_reply=True)

    @botcmd(split_args_with=' ')
    def jira_create(self, msg, args):
        """
        Creates a new issue
        not implemented yet
        """
        return "Not implemented"

    @botcmd(split_args_with=' ')
    def jira_assign(self, msg, args):
        """
        (Re)assigns an issue to a given user
        not implemented yet
        """
        return "Not implemented"
