#---------------------------------------------------------------
# Project         : Mandriva Linux
# Module          : rpmlint
# File            : InitScriptCheck.py
# Version         : $Id$
# Author          : Frederic Lepied
# Created On      : Fri Aug 25 09:26:37 2000
# Purpose         : check init scripts (files in /etc/rc.d/init.d)
#---------------------------------------------------------------

from Filter import *
import AbstractCheck
import Config
import re
import rpm
import Pkg
import string

rc_regex=re.compile('^/etc(/rc.d)?/init.d/')
chkconfig_content_regex=re.compile('# +chkconfig: +([-0-9]+) +[-0-9]+ +[-0-9]+', re.MULTILINE)
subsys_regex=re.compile('/var/lock/subsys/([^/"\'\n\s;&|]+)', re.MULTILINE)
chkconfig_regex=re.compile('^[^#]*(chkconfig|add-service|del-service)', re.MULTILINE)
status_regex=re.compile('^[^#]*status', re.MULTILINE)
reload_regex=re.compile('^[^#]*reload', re.MULTILINE)
basename_regex=re.compile('([^/]+)$')
dot_in_name_regex=re.compile('.*\..*')
use_deflevels=Config.getOption('UseDefaultRunlevels', 1)

class InitScriptCheck(AbstractCheck.AbstractCheck):

    def __init__(self):
        AbstractCheck.AbstractCheck.__init__(self, 'InitScriptCheck')

    def check(self, pkg):
        # Check only binary package
        if pkg.isSource():
            return

        initscript_list = []
        for f in pkg.files().keys():
            if rc_regex.search(f):
                basename=basename_regex.search(f).group(1)
                initscript_list.append(basename)
                if pkg.files()[f][0] & 0500 != 0500:
                    printError(pkg, 'init-script-non-executable',f)

                if dot_in_name_regex.match(basename):
                    printError(pkg, 'init-script-name-with-dot', f)
                # check chkconfig call in %post and %preun
                postin=pkg[rpm.RPMTAG_POSTIN] or pkg[rpm.RPMTAG_POSTINPROG]
                if not postin:
                    printError(pkg, 'init-script-without-chkconfig-postin', f)
                else:
                    if not chkconfig_regex.search(postin):
                        printError(pkg, 'postin-without-chkconfig', f)

                preun=pkg[rpm.RPMTAG_PREUN] or pkg[rpm.RPMTAG_PREUNPROG]
                if not preun:
                    printError(pkg, 'init-script-without-chkconfig-preun', f)
                else:
                    if not chkconfig_regex.search(preun):
                        printError(pkg, 'preun-without-chkconfig', f)

                status_found = 0
                reload_found = 0
                chkconfig_content_found = 0
                subsys_regex_found = 0
                # check common error in file content
                fd=open(pkg.dirName() + '/' + f, 'r')
                for line in fd.readlines():
                    if status_regex.search(line):
                        status_found = 1

                    if reload_regex.search(line):
                        reload_found = 1

                    res = chkconfig_content_regex.search(line)
                    if res:
                        chkconfig_content_found = 1
                        if use_deflevels:
                            if res.group(1) == '-':
                                printWarning(pkg, 'no-default-runlevel', f)
                        else:
                            if res.group(1) != '-':
                                printWarning(pkg, 'service-default-enabled', f)

                    res = subsys_regex.search(line)
                    if res:
                        subsys_regex_found = 1
                        name=res.group(1)
                        if name != basename:
                            error=1
                            if name[0] == '$':
                                value=Pkg.substitute_shell_vars(name, line)
                                if value == basename:
                                    error=0
                            if error:
                                if name[0] == '$':
                                    printWarning(pkg, 'incoherent-subsys', f, name)
                                else:
                                    printError(pkg, 'incoherent-subsys', f, name)

                if not status_found:
                    printError(pkg, 'no-status-entry', f)
                if not reload_found:
                    printWarning(pkg, 'no-reload-entry', f)
                if not chkconfig_content_found:
                    printError(pkg, 'no-chkconfig-line', f)
                if not subsys_regex_found:
                    printError(pkg, 'subsys-not-used', f)

        if len(initscript_list) == 1 and string.lower(pkg.name) != initscript_list[0]:
            printWarning(pkg, 'incoherent-init-script-name', initscript_list[0])


# Create an object to enable the auto registration of the test
check=InitScriptCheck()

if Config.info:
    addDetails(
'init-script-without-chkconfig-postin',
'''The package contains an init script but doesn't contain a %post with
a call to chkconfig.''',

'postin-without-chkconfig',
'''The package contains an init script but doesn't call chkconfig in its %post.''',

'init-script-without-chkconfig-preun',
'''The package contains an init script but doesn't contain a %preun with
a call to chkconfig.''',

'preun-without-chkconfig',
'''The package contains an init script but doesn't call chkconfig in its %preun.''',

'no-status-entry',
'''In your init script (/etc/rc.d/init.d/your_file), you don't
have a 'status' entry, which is necessary for good functionality.''',

'no-reload-entry',
'''In your init script (/etc/rc.d/init.d/your_file), you don't
have a 'reload' entry, which is necessary for good functionality.''',

'no-chkconfig-line',
'''The init script doesn't contain a chkconfig line to specify the runlevels
at which to start and stop it.''',

'no-default-runlevel',
'''The default runlevel isn't specified in the init script.''',

'service-default-enabled',
'''The service is enabled by default after "chkconfig --add"; for security
reasons, most services should not be. Use "-" as the default runlevel in the
init script's chkconfig line to fix this if appropriate for this service.''',

'subsys-not-used',
'''While your daemon is running, you have to put a lock file in
/var/lock/subsys/. To see an example, look at this directory on your
machine and examine the corresponding init scripts.''',

'incoherent-subsys',
'''The filename of your lock file in /var/lock/subsys/ is incoherent
with your actual init script name. For example, if your script name
is httpd, you have to use 'httpd' as the filename in your subsys directory.
It is also possible that rpmlint gets this wrong, especially if the init
script contains nontrivial shell variables and/or assignments.  These
cases usually manifest themselves when rpmlint reports that the subsys name
starts a with '$'; in these cases a warning instead of an error is reported
and you should check the script manually.''',

'incoherent-init-script-name',
'''The init script name should be the same as the package name in lower case.''',

'init-script-name-with-dot',
'''The init script name should not contain a dot in its name. Some versions
of chkconfig don't work as expected with init script names like that.''',

'init-script-non-executable',
'''The init script should have at least the execution bit set for root
in order for it to run at boot time.''',
)

# InitScriptCheck.py ends here

# Local variables:
# indent-tabs-mode: nil
# py-indent-offset: 4
# End:
# ex: ts=4 sw=4 et
