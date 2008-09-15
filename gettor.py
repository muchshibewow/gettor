#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
"""

 gettor.py by Jacob Appelbaum <jacob@appelbaum.net>
 This program will hand out Tor via email to supported systems.
 This program is Free Software, see LICENSE for details.

 It is intended to be used in a .forward file as part of a pipe like so:

     cat <<'EOF'> .forward
     |/usr/local/bin/gettor.py
     EOF

 You should have a dist/current/ mirror in a directory that gettor can read.
 Such a mirror can be created like so:

     cd /usr/local/
     rsync -av rsync://rsync.torproject.org/tor/dist/current tor-dist-current/

 You can keep it updated with a cronjob like so:

     MirrorDir=/usr/local/tor-dist-current/
     0 3 * * * rsync -a rsync://rsync.torproject.org/tor/dist/current/ $MirrorDir
 
 You should ensure that for each file and signature pair you wish to 
 distribute, you have created a zip file containing both.

 While this program isn't written in a threaded manner per se, it is designed to function 
 as if it will be called as a pipe many times at once. There is a slight 
 desynchronization with blacklist entry checking and may result in false 
 negatives. This isn't perfect but it is designed to be lightweight. It could 
 be fixed easily with a shared locking system but this isn't implemented yet.

 To clean out the blacklist on a daily basis, install the following cronjob:

     # m h  dom mon dow   command
     1 1 * * * /bin/rm -rf /var/lib/gettor/bl/*

 You'll probably want a directory structure like this owned by uid/gid 'gettor':
    /var/lib/gettor/{bl,pkg}

"""

__program__ = 'gettor.py'
__version__ = '20080914.01'
__url__ = 'https://tor-svn.freehaven.net/svn/tor/trunk/contrib/gettor/'
__author__ = 'Jacob Appelbaum <jacob@appelbaum.net>'
__copyright__ = 'Copyright (c) 2008, Jacob Appelbaum'
__license__ = 'See LICENSE for licensing information'

try:
    from future import antigravity
except ImportError:
    antigravity = None

import gettor_blacklist
import gettor_requests
import gettor_responses
from gettor_log import gettorLogger

log = gettorLogger()

if __name__ == "__main__":


    rawMessage = gettor_requests.getMessage()
    parsedMessage = gettor_requests.parseMessage(rawMessage)

    if not parsedMessage:
        log.log("No parsed message. Dropping message.")
        exit(0)

    signature = False
    signature = gettor_requests.verifySignature(rawMessage)
    log.log("Signature is : " + str(signature))
    replyTo = False
    srcEmail = "gettor@torproject.org"

    # TODO XXX:
    # Make the zip files and ensure they match packageList
    # Make each zip file like so:
    # zip -9 windows-bundle.z \
    #   vidalia-bundle-0.2.0.29-rc-0.1.6.exe \
    #   vidalia-bundle-0.2.0.29-rc-0.1.6.exe.asc
    #
    distDir = "/var/lib/gettor/pkg/"
    packageList = {
        "windows-bundle": distDir + "windows-bundle.z",
        "macosx-panther-ppc-bundle": distDir + "macosx-panther-ppc-bundle.z",
        "macosx-tiger-universal-bundle": distDir + "macosx-tiger-universal-bundle.z",
        "source-bundle": distDir + "source-bundle.z"
        }

    # XXX TODO: Ensure we have a proper replyTO or bail out (majorly malformed mail).
    replyTo = gettor_requests.parseReply(parsedMessage)
    
    if not signature:
        # Check to see if we've helped them to understand that they need DKIM in the past
        previouslyHelped = gettor_blacklist.blackList(replyTo)
    
    if not replyTo:
        log.log("No help dispatched. Invalid reply address for user.")
        exit(0)

    if not signature and previouslyHelped:
        log.log("Unsigned messaged to gettor by blacklisted user dropped.")
        exit(0)

    if not signature and not previouslyHelped:
        # Reply with some help and bail out
        gettor_blacklist.blackList(replyTo, True)
        message = """
Hello! This is the "get tor" robot.

Unfortunately, we won't answer you at this address. We only process
requests from email services that support "DKIM", which is an email
feature that lets us verify that the address in the "From" line is
actually the one who sent the mail.

Gmail and Yahoo Mail both use DKIM. You will have better luck sending
us mail from one of those.

(We apologize if you didn't ask for this mail. Since your email is from
a service that doesn't use DKIM, we're sending a short explanation,
and then we'll ignore this email address for the next day or so.)
        """
        gettor_responses.sendHelp(message, srcEmail, replyTo)
        log.log("Unsigned messaged to gettor. We issued some help about using DKIM.")
        exit(0)

    if signature:
        log.log("Signed messaged to gettor.")
        
        try:
            package = gettor_requests.parseRequest(parsedMessage, packageList)
        except:
            package = None

        if package != None:
            log.log("Package: " + str(package) + " selected.")
            message = "Here's your requested software as a zip file. Please " + \
            "unzip the package and verify the signature."
            gettor_responses.sendPackage(message, srcEmail, replyTo, packageList[package])  
            exit(0)
        else:
            message = ["Hello, I'm a robot. "]
            message.append("Your request was not understood. Please select one of the following package names:\n")

            for key in packageList.keys():
                message.append(key + "\n")
            message.append("Please send me another email. It only needs a single package name anywhere in the body of your email.\n")
            gettor_responses.sendHelp(''.join(message), srcEmail, replyTo)
            log.log("Signed messaged to gettor. We issued some help about proper email formatting.")
            exit(0)
