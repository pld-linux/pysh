#!/usr/bin/env python
#
# PySH by Geoff Howland
#
# Version 0.04
#
# Original version: 05-09-04
# Current version:  05-11-04
#
# License: BSD License:  
#          http://www.opensource.org/licenses/bsd-license.php
#          So do what you want with it.
#

import token, tokenize, cStringIO
import os
import sys
import socket
import string
import re

# Im importing specific commands, because I dont want to clutter the 
#   globals at startup
from pprint import pprint
#from pyclbr import readmodule_ex
from inspect import getsource
from inspect import getmembers

from types import ModuleType
"""Used for tab completion to check globals for modules."""

TOK_TYPE = 0
TOK_TEXT = 1
TOK_START = 2
TOK_STOP = 3
TOK_FULLTEXT = 4
"""Tokenize generate_tokens() tuple position types."""

TOK_BREAKS = [':', '\n', '\r', '|', ';', '{,' '}']
"""These characters force new words."""

LINE_BREAK_CHARS = [':', ';', '\n']
"""These characters force this to be treated as a new line."""

class Parser:
  def __init__(self):
    pass

  def Parse(self, text, _locals={}, _globals={}, builtins=[], get_command_line=0):
    """Parse the text into Python code, using locals and globals specified
          to check against variables.
    
       builtins is a list of names of functions that we will NOT allow 
          to be OS commands.
    
       If get_command_line is set, this function returns whether or not we
          are currently in a command line, and NOT the output of the parse.
    """
    self._locals = _locals
    self._globals = _globals
    self.builtins = builtins
    
    self.indent = 0
    
    word = ''
    
    # Our final outut
    self.output = ''
    
    # If we are processing a command, we do it separately from normal output
    self.command_output = ''
    self.command_line = False
    
    # We want to be able to chain commands by pipes and redirects
    self.command_list = []
    
    # We count which word in the line it is, to look for commands
    self.line_word_count = 0
    
    # Create token generator
    g = tokenize.generate_tokens(cStringIO.StringIO(text).readline)
    
    # We dont have a Last Token yet
    last_tok = None
    
    # How many spaces in front of the word we are processing
    pre_space = 0
    
    # Process token generator
    for tok in g:
      # Ignore spacing, it is unreliable for some reason
      if tok[TOK_TYPE] == 5:
        continue
      
      # If this is the first line, or we dont have a word string yet
      if not last_tok or not word:
        word += tok[TOK_TEXT]
        # We dont want to lose our leading spaces
        pre_space = tok[TOK_START][1]
      else:
        # Check to see if this is a new word (by spacing), or we moved lines,
        #   or this is a character we consider to be a word break
        if last_tok[TOK_STOP][1] != tok[TOK_START][1] \
              or last_tok[TOK_START][0] != tok[TOK_START][0] \
              or tok[TOK_TEXT] in TOK_BREAKS:
          # Process the word we had so far
          self.ProcessWord(word, pre_space)
          
          # Increment the line word count
          self.line_word_count += 1
          
          # This token is our new word
          word = tok[TOK_TEXT]
          
          # We want to make sure if we are declaring a new variable in a for loop, 
          #   and we are going to run commands off of it, we have to declare it
          #   first, so we do
          #NOTE(ghowland): SPECIAL CASE for the for loop
          if last_tok[TOK_TEXT] == 'for' and tok[TOK_TYPE] == 1 and tok[TOK_TEXT] not in self._locals and tok[TOK_TEXT] not in self._globals:
            self._globals[tok[TOK_TEXT]] = None
          
          # We want to make sure if we are declaring a new variable an assignment.
          #NOTE(ghowland): SPECIAL CASE for assignment operator (=)
          if tok[TOK_TEXT] == '=' and last_tok[TOK_TYPE] == 1 and last_tok[TOK_TEXT] not in self._locals and last_tok[TOK_TEXT] not in self._globals:
            self._globals[last_tok[TOK_TEXT]] = None
          
          # If this is a new line, reset the word count
          if last_tok[TOK_START][0] != tok[TOK_START][0]:
            # Determine how many spaces to put in front of the new word
            pre_space = tok[TOK_START][1]
            
            if self.command_line:
              self.output += 'ProcessCommand("""%s""" %% locals())' % \
                    self.command_output.replace('\n', '').replace('\r', '')
                    
            self.line_word_count = 0
            # We are not in a command line, cause its a new line
            self.command_line = False
            self.command_output = ''
          else:
            # Determine how many spaces to put in front of the new word
            pre_space = tok[TOK_START][1] - last_tok[TOK_STOP][1]
          
          # This doesnt effect the output, but it does effect commands, so
          #   process it now
          if self.line_word_count != 0 and tok[TOK_TEXT] in LINE_BREAK_CHARS:
            self.line_word_count = -1
            if self.command_line:
              self.output += 'ProcessCommand("""%s""" %% locals())' % \
                    self.command_output.replace('\n', '').replace('\r', '')
            self.command_line = False
            self.command_output = ''
            
        # Else, this token does not have space separation
        else:
          word += tok[TOK_TEXT]
        
      # Save the token, so we can compare it with the next one
      last_tok = tok
    
    # If we have a word left unprocessed, process it
    if word:
      self.ProcessWord(word, pre_space)
    
    # Try to add in {} evals
    lines = self.output.split('\n')
    final_lines = []
    for count in range(len(lines)):
      eval_count = 0
      # No good way to loop here, so im doing it the long way
      done = False
      while not done:
        # re.match fails to work, AT ALL.  So I have to use findall to find 
        #   if there are any matches.  If not, we're done on this line
        if not re.findall('{.*?}', lines[count]):
          done = True
          continue
        
        # There are matches, and I want a match object.  But since match 
        #   fails to work on {} characters, I will use finditer which
        #   returns a generator that returns match objects.  We only want
        #   the first one, and there always is one from above.
        #TODO(ghowland): Remove the lame suckitude that is this multi-REing.
        item = re.finditer('{.*?}', lines[count]).next()
      
        # Process our eval
        eval_str = item.group()[1:-1]
        var_name = '__line_%d_%d' % (count+1, eval_count)
        #NOTE(ghowland): Im adding in an extra space in the triple quotes so 
        #   that an accidental double quote at the end wont fuck things up.
        eval_line = '%s = eval("""%s """)' % (var_name, eval_str)
        # We need the indentation of the current line
        line_indent = re.findall('^[ ]*', lines[count])[0]
        # Add our new variable eval line
        final_lines.append(line_indent + eval_line)
        # Change our current line.  We may do this several times if there are more matches
        lines[count] = lines[count][:item.start()] + '%(' + var_name + ')s' + lines[count][item.end():]
      # Add our changed 
      final_lines.append(lines[count])
    
    # Create our new final output
    final_output = string.join(final_lines, '\n')
    if 0:
      print final_output  # Debug
    
    # Return our new {} parsed output
    return final_output
    #return self.output

  def ProcessWord(self, word, pre_space):
    # Check to see if this is the first argument and is an OS command, 
    #   and its not a builtin
    if self.line_word_count == 0 and self.FindNameInPath(word) and word not in self.builtins:
      #self.output += ' ' * pre_space
      self.output += '  ' * self.indent
      self.command_line = True
      self.command_output += self.FindNameInPath(word)
    # Else if this is just the first argument, and not an OS command
    elif self.line_word_count == 0:
      # If this is a conditional extension, auto-reduce the indent.
      #   It will be pushed out again by the colon at the end of the line.
      if word in ('else', 'elif'):
        self.indent -= 1
      # Only put the spaces for indent, this is the first word so ignore and prefixing space
      self.output += '  ' * self.indent
      self.output += word
      
      # We need a mechanism for being able to reduce indents, Im goin to use this to do that
      #NOTE(ghowland): This needs to happen after the word is printed, because we want it
      #   on the same line if copy and pasted back in later.
      if word == 'pass':
        self.indent -= 1
    # Else, this isnt the first argument
    else:
      # If this isnt a command line, just add the word
      if not self.command_line:
        self.output += ' ' * pre_space
        # Try to work around the multiple nest problem
        if word == ':':
          # We want to print this out
          self.output += word
          self.output += '\n'
          # Increase our indent each line
          self.indent += 1
        # Another line to process
        #NOTE(ghowland): We arent printing this out, its pointless
        elif word == ';':
          self.output += '\n'
        else:
          self.output += word
      # Else, this is a command line so we have to do some checking
      else:
        # Check if this is a file in the cwd (or qualified)
        if self.FindNameInFS(word):
          self.command_output += ' ' * pre_space
          self.command_output += self.FindNameInFS(word)
        # Else, evaluate it as a possible variable
        else:
          self.command_output += ' ' * pre_space
          self.command_output += self.FindNameInEval(word)

  def FindNameInPath(self, name, env='PATH'):
    """Find the name in the path.  Can specify alternative path env var."""
    for dir in os.environ[env].split(os.pathsep):
      if os.path.exists(dir + '/' + name):
        return name
      #if os.name == 'nt':
      #  if os.path.exists(dir + '/' + name + '.exe'):
      #    return name
    
    if os.path.exists(name):
      return name
    
    return None
  
  def FindNameInFS(self, name):
    """Find the name in the file system, from the current directory."""
    if os.path.exists(name):
      return name
    
    return None
  
  def FindNameInEval(self, name):
    """Try to evaluate the name, return it as a string.  Convert lists/dicts.
        NOTE(ghowland): This should ONLY be done for arguments in a command, NOT
            normal python commands.  If the first argument in a line is found
            in the path, then this is a command line and args should be eval'd.
            Otherwise, do not do this as it will screw up Python code processing.
    """
    # If this name isnt in our variables, then return it as a string
    #   Avoids things that eval, but we dont want to
    if name not in self._locals and name not in self._globals:
      return str(name)
    else:
      return '%%(%s)s' % name

def ProcessCommand(cmd, print_command=1):
  """Process this command to completion, printing the output/error"""
  
  # Skip all the other crap and call right out to system
  return os.system(cmd)



#NOTE(ghowland): Thanks James.  Your Console implementation made it easier 
#   for me to get this working!

## console.py
## Author:   James Thiele
## Date:     27 April 2004
## Version:  1.0
## Location: http://www.eskimo.com/~jet/python/examples/cmd/
## Copyright (c) 2004, James Thiele

import os
import cmd
import readline

class Console(cmd.Cmd):
  def __init__(self):
    cmd.Cmd.__init__(self)
    try:
      self.username = os.getlogin()
    except:
      self.username = os.environ.get('USER', os.environ.get('USERNAME', ''))
    
    # NT Fix
    if 'PWD' not in os.environ:
      os.environ['PWD'] = os.path.realpath(os.curdir)
    
    # Save the username and other important variables
    os.environ['USER'] = self.username
    os.environ['HOSTNAME'] = socket.gethostname().split('.')[0]
    
    os.environ['PY_PS1'] = '[%(USER)s@%(HOSTNAME)s %(PWD)s]$ '
    self.prompt = os.environ['PY_PS1'] % os.environ
    self.intro  = "Welcome to PySH!"  ## defaults to None
    
    self.parser = Parser()
    
    # Debug off by default
    self.debug = False


  ## Command definitions ##
  def do_hist(self, args):
    """Print a list of commands that have been entered"""
    print self._hist

  def do_exit(self, args):
    """Exits from the console"""
    sys.exit(0)
    return -1

  def do_debug_toggle(self, args):
    """Exits from the console"""
    self.debug = not self.debug
    if self.debug:
      print 'Debugging on.'
    else:
      print 'Debugging off.'

  ## Command definitions to support Cmd object functionality ##
  def do_EOF(self, args):
    """Exit on system end of file character"""
    return self.do_exit(args)

  def do_shell(self, args):
    """Pass command to a system shell when line begins with '!'"""
    os.system(args)

  def do_import(self, args):
    globals()[args] = __import__(args)

  def do_export(self, args):
    #TODO(ghowland): Strip the args before passing in, so we dont have this everywhere
    if not args.strip():
      # Print out the environment dict
      print '{'
      for key in os.environ:
        print " '%s': '%s', " % (key, os.environ[key].replace("'", "\\'"))
      print '}'
    else:
      # Assignment export
      if args.find('=') != -1:
        key, value = args.split('=', 1)
        try:
          os.environ[key.strip()] = eval(value)
        except NameError:
          os.environ[key.strip()] = value.strip()
        
        # Add the variable to the globals
        self._globals[key] = os.environ[key]
      # Current value export
      else:
        key = args.strip()
        if key in self._locals:
          os.environ[key] = str(self._locals[key])
        elif key in self._globals:
          os.environ[key] = str(self._globals[key])
        else:
          os.environ[key] = ''
        
        # Add the variable to the globals, it may already be there, but 
        #   we want to insist
        self._globals[key] = os.environ[key]

  def do_python_line(self, args):
    """Pass command to a system shell when line begins with '^'"""
    exec(args) in self._locals, self._globals

  def do_pyls(self, args):
    """List the methods and functions in modules."""
    print 'TBD.'
    
  def do_pyls(self, args):
    """List members of an object."""
    try:
      print '[',
      for member in getmembers(eval(args)):
        print "'%s', " % member[0], 
      print ']'
    except IOError, e:
      print 'Python IOError: %s' % e

  def do_pycat(self, args):
    """Print the source to a module we have imported."""
    #TODO(ghowland): Pycat functions, classes, etc from source as well.
    try:
      print getsource(eval(args))
    except IOError, e:
      print 'Python IOError: %s' % e

    if 0:
      module_list = args.split('.')
      module = module_list[0]
      # Take the last name, however many their are, we will pretend were smart
      function = module_list[-1]
      # Lets start looking for the module
      if module in self._globals and type(self._globals[module]) == ModuleType:
        if self._globals[module].__file__[-4:] == '.pyc':
          # We have the module, and its source file
          filename = self._globals[module].__file__[:-1]
          if os.path.isfile(filename):
            # We know the file exists, do we want the whole thing or just a function?
            if len(module_list) == 1:
              # The whole file
              print open(filename).read()
            else:
              # Just print a function
              parsed = readmodule_ex(module)
              # Loop over all the classes we have
              for key in parsed:
                # If this is a class
                if 'methods' in parsed[key].__dict__:
                  # Sort the dictionary by values
                  items = [(v, k) for k, v in parsed[key].methods.items()]
                  items.sort()
                  for count in range(len(items)):
                    if function == items[count][1]:
                      line_start = items[count][0] - 1
                      if count != len(items)-1:
                        line_end = items[count+1][0] - 1
                      else:
                        line_end = None
                      # Load the file, and print these lines
                      lines = open(filename).readlines()
                      if line_end:
                        print string.join(lines[line_start:line_end])
                      else:
                        #TODO(ghowland): BUG!  This wont work, we will print 
                        #   out the whole file.  We need to search for the
                        #   next non-starting character, like for functions.
                        print string.join(lines[line_start:])
                      # Were done, dont look any more
                      return
                # If this is a function, and it matches our function name
                #TODO(ghowland): Can code duplication be avoided here?  
                #   Maybe turn this into a function.
                elif function == key and 'lineno' in parsed[key].__dict__:
                  line_start = parsed[key].lineno - 1
                  # How do we process the last line?  It could be anywhere...
                  #   No.  We can look for the next non-comment line in the source.
                  # Load the file, and start printing lines tell we find another 
                  #   non-comment character on the first line.
                  lines = open(filename).readlines()
                  count = line_start
                  while count < len(lines):
                    print lines[count],
                    count += 1
                    #TODO(ghowland): This isnt an accurate test, things like tripple
                    #   quoted strings on the beginning of the line will mess 
                    #   this up.  But it will be HARD to figure it out.  Will
                    #   have to built up ALL functions and everything else and sort
                    #   them to fix this.  Do it later.
                    if count >= len(lines) or (lines[count][0] not in (' ', '\t') and len(lines[count].strip()) != 0):
                      break
                  # Were done, dont look any more
                  return
          else:
            print "Source for module '%s' not found at %s" % (module, filename)
        else:
          print "Imported module '%s' is not Python bytecode: %s" % (module, self._globals[module].__file__)
      else:
        print "Module '%s' not imported." % module

  def do_cd(self, args):
    """Change directory"""
    if not args:
      args = os.environ['HOME']
    
    # If there is a tilda (home character), and it isnt escaped
    if args.find('~') != -1 and (args.find('\\~') == -1 or args.find('~') != args.find('\\~') + 1):
      args = args.replace('~', os.environ['HOME'])
    
    # Change dir
    try:
      os.chdir(args)
    except OSError, e:
      print 'Python OSError: %s' % e
    
    # Save the CWD
    os.environ['PWD'] = os.getcwd()

    #self.prompt = "[%s@%s %s]$ " % (self.username, socket.gethostname().split('.')[0], os.getcwd())
    self.prompt = os.environ['PY_PS1'] % os.environ
    
  def do_print(self, args):
    """Print builtin.  Print Python variables, and strings."""
    try:
      print eval(args)
    except NameError:
      print args
    except SyntaxError:
      print args

  def do_pprint(self, args):
    """Pretty print"""
    pprint(eval(args))

  def do_pyhelp(self, args):
    """Python document help."""
    help(args)

  def do_help(self, arg):
    """Get help on commands
       'help' or '?' with no arguments prints a list of commands for which help is available
       'help <command>' or '? <command>' gives help on <command>
    """
    if arg:
      # XXX check arg syntax
      try:
        func = getattr(self, 'help_' + arg)
      except AttributeError:
        try:
          doc=getattr(self, 'do_' + arg).__doc__
          if doc:
            self.stdout.write("%s\n"%str(doc))
            return
        except AttributeError:
          # Help for global modules
          if arg in self._globals:
            print self._globals[arg].__doc__
            return

          # Help for global module members
          args = arg.split('.')
          if args[0] in self._globals and len(args) == 2:
            print self._globals[args[0]].__dict__[args[1]].__doc__
            return

          #TODO(ghowland): Have help for any depth of things.

        self.stdout.write("%s\n"%str(self.nohelp % (arg,)))
        return
      func()
    else:
        names = self.get_names()
        cmds_doc = []
        cmds_undoc = []
        help = {}
        for name in names:
            if name[:5] == 'help_':
                help[name[5:]]=1
        names.sort()
        # There can be duplicates if routines overridden
        prevname = ''
        for name in names:
            if name[:3] == 'do_':
                if name == prevname:
                    continue
                prevname = name
                cmd=name[3:]
                if cmd in help:
                    cmds_doc.append(cmd)
                    del help[cmd]
                elif getattr(self, name).__doc__:
                    cmds_doc.append(cmd)
                else:
                    cmds_undoc.append(cmd)
        # Process the global modules
        doc_modules = []
        # Now get all the modules we have imported
        for key in self._globals:
          if type(self._globals[key]) == ModuleType:
            # Ignore names that we dont want to show
            if key not in ('__builtins__',):
              # Make sure it matches our type
              if self._globals[key].__doc__:
                doc_modules.append(key)
        
        self.stdout.write("%s\n"%str(self.doc_leader))
        self.print_topics(self.doc_header,   cmds_doc,   15,80)
        self.print_topics(self.misc_header,  help.keys(),15,80)
        self.print_topics(self.undoc_header, cmds_undoc, 15,80)
        self.print_topics("Modules:", doc_modules, 15,80)


  ## Override methods in Cmd object ##
  def preloop(self):
    """Initialization before prompting user for commands.
       Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
    """
    cmd.Cmd.preloop(self)   ## sets up command completion
    self._hist    = []      ## No history yet
    self._locals  = {}      ## Initialize execution namespace for user
    self._globals = globals()
    
    # Populate the globals with environment vars
    for key in os.environ:
      self._globals[key] = os.environ[key]

    # Get our builtin function names, and add them to the locals
    self.reserved_funcs = [a[3:] for a in self.get_names() if a.startswith('do_')]
    for func_name in self.reserved_funcs:
      # Strip off the leading 'do_'
      self._locals['do_%s' % func_name] = getattr(self, 'do_%s' % func_name)

  def postloop(self):
    """Take care of any unfinished business.
       Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
    """
    cmd.Cmd.postloop(self)   ## Clean up command completion
    print "Exiting..."

  def precmd(self, line):
    """ This method is called after the line has been input but before
        it has been interpreted. If you want to modifdy the input line
        before execution (for example, variable substitution) do it here.
    """
    self._hist += [ line.strip() ]
    return line

  def postcmd(self, stop, line):
    """If you want to stop the console, return something that evaluates to true.
       If you want to do some post command processing, do it here.
    """
    return stop

  def emptyline(self):    
    """Do nothing on empty input line"""
    pass


  def completenames(self, text, *ignored):
      dotext = 'do_'+text
      # Get our function names
      our_names = [a[3:] for a in self.get_names() if a.startswith(dotext)]
      # Now get all the modules we have imported
      for key in self._globals:
        if type(self._globals[key]) == ModuleType:
          # Ignore names that we dont want to show
          if key not in ('__builtins__',):
            # Make sure it matches our type
            if key.startswith(text):
              our_names.append(key)
      
      return our_names

  def parseline(self, line):
      line = line.strip()
      if not line:
          return None, None, line
      elif line[0] == '?':
          line = 'help ' + line[1:]
      elif line[0] == '!':
          if hasattr(self, 'do_shell'):
              line = 'shell ' + line[1:]
          else:
              return None, None, line
      elif line[0] == '^':
          if hasattr(self, 'do_python_line'):
              line = 'python_line  ' + line[1:]
          else:
              return None, None, line
      i, n = 0, len(line)
      while i < n and line[i] in self.identchars: i = i+1
      cmd, arg = line[:i], line[i:].strip()
      return cmd, arg, line

  def cmdloop(self, intro=None):
    """Repeatedly issue a prompt, accept input, parse an initial prefix
    off the received input, and dispatch to action methods, passing them
    the remainder of the line as argument.

    """

    self.preloop()
    if intro is not None:
      self.intro = intro
    if self.intro:
      self.stdout.write(str(self.intro)+"\n")
    stop = None
    while not stop:
      if self.cmdqueue:
        line = self.cmdqueue.pop(0)
      else:
        if self.use_rawinput:
          try:
            line = raw_input(self.prompt)
          except EOFError:
            line = 'EOF'
          except KeyboardInterrupt:
            # Ignore CRTL-Cs, clear the line variable and print a newline
            line = ''
            self.stdout.write('\n')
        else:
          self.stdout.write(self.prompt)
          self.stdout.flush()
          line = self.stdin.readline()
          if not len(line):
            line = 'EOF'
          else:
            line = line[:-1] # chop \n
      line = self.precmd(line)
      stop = self.onecmd(line)
      stop = self.postcmd(stop, line)
    self.postloop()

  def default(self, line):       
    """Called on an input line when the command prefix is not recognized.
       In that case we execute the line as Python code.
    """
    try:
      #exec(line) in self._locals, self._globals
      # Use the Parser to be able to do Python and shell together
      try:
        # Parse the line we received
        output = self.parser.Parse(line, self._locals, self._globals, self.reserved_funcs)
        
        # Process the lines looking for our builtin commands
        lines = output.split('\n')
        for count in range(len(lines)):
          words = lines[count].split(' ')
          # If this is a builtin word, join the line back together inside a 
          #   function call to our builtin.  We know this will work, cause
          #   we just pushed the functions into locals above.
          if words[0] in self.reserved_funcs:
            # We need to add the 'do_' back
            lines[count] = 'do_%s("""%s""")'  % (words[0], string.join(words[1:], ' ').strip())
        
        # Reform the output
        output = string.join(lines, '\n')
        
        # Print our python code, if were debugging
        if self.debug:
          print output
        
        # Execute the output
        exec(output) in self._locals, self._globals
        
      except NameError, e:
        sys.stderr.write('Python NameError: %s or file not found\n' % e)
      except AttributeError, e:
        sys.stderr.write('Python AttributeError: %s\n' % e)
      except SyntaxError, e:
        sys.stderr.write('Python SyntaxError: %s\n' % e)
      except TypeError, e:
        sys.stderr.write('Python TypeError: %s\n' % e)
    except SystemExit, e:
      sys.exit(e)
    except Exception, e:
      print e.__class__, ":", e

  def onecmd(self, line):
    """Interpret the argument as though it had been typed in response
    to the prompt.

    This may be overridden, but should not normally need to be;
    see the precmd() and postcmd() methods for useful execution hooks.
    The return value is a flag indicating whether interpretation of
    commands by the interpreter should stop.

    """
    cmd, arg, line = self.parseline(line)
    if not line:
      return self.emptyline()

    # We are going to force everything through default(), because we want
    #   to parse things.  We could really just parse things here though.
    #TODO(ghowland): Parse things here, and figure out the best way to 
    #   continue.  Also, we are barely using Cmd anymore probably, we
    #   should refactor it out soon.
    return self.default(line)



def main():
  console = Console()
  console.cmdloop()

if __name__ == '__main__':
  main()
