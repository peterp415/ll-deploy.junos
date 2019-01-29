#!/usr/bin/env python

import re

class FilterModule(object):
    def filters(self):
        return {
            're_for_redundancy_group': self.re_for_redundancy_group
        }

    def re_for_redundancy_group(self, show_chassis_cluster, search_primary=True):
        '''
        The variable `show_chassis_cluster` should contain the stdout output of
        the 'show chassis cluster status' command.  The filter will return the
        current node that is primary for the given redundancy-group.  As this is
        a workaround the below ansible snippet will provide the needed output
        junos_command:
          commands: show chassis cluster status redundancy-group 0
          display: text
        register: result
        set_fact:
            is_primary: "{{ result.stdout | re_for_redundancy_group(true) }}"
            is_secondary: "{{ result.stdout | re_for_redundancy_group(false) }}"
        '''
        regex=r'^(node(0|1))\s+[0-9]{1,3}\s+'
        if search_primary:
            regex=regex + 'primary'
        else:
            regex=regex + 'secondary'

        for item in show_chassis_cluster:
            # Search for the line that has node0 or node1 as primary
            result = re.search(regex, item, re.M)
            if result:
                return result.group(1)
            else:
                return None
