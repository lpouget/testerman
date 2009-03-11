# -*- coding: utf-8 -*-
##
# This file is part of Testerman, a test automation system.
# Copyright (c) 2008-2009 Sebastien Lefevre and other contributors
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
##

##
# Base interface/class to implement FileSystemBackends (FSB)
#
##

class Attributes:
	def __init__(self):
		# File size, in bytes
		self.size = None
		# Last modification timestamp, float
		self.mtime = None
		# username, if applicable, string
		self.username = None
		# group, if applicable, string
		self.group = None
		

class FileSystemBackend:
	"""
	Base class to subclass when creating new backend plugins.
	
	This base class provides the testerman FSB interface to manipulate a filesystem
	(a subset of the FUSE interface).
	
	FSBs are configurable through "properties" that are set when instantiating
	the plugin instance from the FileSystemBackendManager, when attaching it
	to a mounting point in the exposed, virtual testerman file system view.
	
	It's no use creating thread-safe plugins, since the FileSystemManager
	ensures to access files in a non-concurrent manner (per plugin instance).
	
	All paths and filenames passed as argument to the FSB methods are
	relative to the FSB instance mountpoint, and does NOT start with a '/'.
	"""
	
	SCOPE_LOCAL = 0
	SCOPE_SUBTREE = 1
	
	def __init__(self):
		self.__properties = {}
		self._type = 'undefined'
	
	def _setType(self, type_):
		self._type = type_
	
	def setProperty(self, name, value):
		self.__properties[name] = value

	def getProperty(self, name, defaultValue):
		return self.__properties.get(name, defaultValue)

	def __getitem__(self, name):
		if self.__properties.has_key(name):
			return self.__properties[name]
		return None
	
	def __str__(self):
		return "'%s' {%s}" % (self._type, ', '.join([ '%s=%s' % (str(x), str(y)) for x, y in self.__properties.items()]))

	##
	# To reimplement in your own file system backends
	##	
	def initialize(self):
		"""
		Initializes the backend.
		Properties are already set when calling it.
		Here you have an opportunity to prepare your plugin.
		(prepare remote connections, VCS login, ...)
		
		@rtype: bool
		@returns: True if OK, False otherwise (typically raise exceptions)
		"""
		return True
	
	# FS operations
	# - no symlink support,
	# - most file attributes are ignored
	# - no open/release/flush methods
	
	def read(self, filename, revision = None):
		"""
		Returns the content of a file.
		Should returns the file exactly as stored through write()
		
		@type  filename: string
		@param filename: the complete path to the file relative to the FSB mountpoint
		@type  revision: string
		@param revision: in case of versioned backends, the revision ID of the file
		                 to retrieve.
		
		@rtype: string/buffer
		@return: the content of the (optionally versioned) file if found,
		         or None if not found.
		"""
		return None

	def write(self, filename, content, baseRevision = None, reason = None):
		"""
		Writes content to a file, creating it if needed.
		The path to the filename should already exist.
		The implementation is responsible for flushing the content if needed.
		
		If baseRevision is provided, you should create a file revision based on baseRevision,
		optionally indicating a reason for the committed revision provided by reason.
		
		If not ... ?

		Dev note:
		we would need something to explicitly commit a file and then creates the
		revision.
		When just "saving" the file, if it creates a new revision each time,
		we'll run a risk of getting too many files in a VCS backend.
		A temporary, server-side but local file write if not committed ?
		(thus still shared amongst the different clients, however, with typical
		optimistic locking if several users are working on the save revision file ?)

		@type  filename: string
		@param filename: the complete filename of the file to create
		@type  content: string/buffer
		@param content: the content to write to filename
		@type  baseRevision: string
		@param baseRevision: branching revision. None for head (if applicable).
		@type  reason: string (utf8)
		@param reason: the optional reason for a revision

		@throws Exception in case of an error

		@rtype: string, or None
		@returns: the newly added file revision, or None if no file revision was created.
		"""
		raise Exception('Not implemented')

	def unlink(self, filename, reason = None):
		"""
		Removes a file.
		Notice that it does not affect its existing revisions, if any.

		@rtype: bool
		@returns: True if OK, False otherwise (typically raise exceptions in case of errors)
		"""
		return False

	def getdir(self, path):
		"""
		Reads the contents of a directory.
		
		Notice directories are not versioned.
		
		@type  path: the path of the dir
		@param path: the path to the dir, relative to the mountpoint

		@rtype: list of dict{'name': string, 'type': string in ['file', 'directory'] }
		@returns: None in case of an error (or non existing directory)
		"""
		return None
	
	def mkdir(self, path):
		"""
		Creates a directory.
		
		Returns True if the directory was created or already existed.

		@rtype: bool
		@returns: True if OK, False otherwise (typically raise exceptions in case of errors)
		"""
		return False
	
	def rmdir(self, path):
		"""
		Removes an *empty* directory.
		
		If the directory is not empty, returns False.
		Returns True if the directory was actually removed or does not exist.

		@rtype: bool
		@returns: True if OK, False otherwise (typically raise exceptions in case of errors)
		"""
		return False
	
	def attributes(self, filename, revision = None):
		"""
		Returns file attributes.
		
		@rtype: FileSystemBacked.Attributes
		@returns: a filled FileSystemBackend.Attributes instance
		          (at least with mtime), or None if the file was not found.
		"""
		return None
	
	def revisions(self, filename, baseRevision = None, scope = SCOPE_LOCAL):
		"""
		Returns a list of revisions that start (branch) from baseRevision.
		If baseRevision is None, then consider the baseRevision is the implicit root of all revisions.
		Returns None if the baseRevision is invalid.
		May return an empty list for leaf revisions.
		
		if scope is SCOPE_LOCAL, only returns direct children revisions.
		If scope is SCOPE_SUBTREE, constructs a list that flattens the complete revision tree from 
		baseRevision.
		
		Ex:
		Existing revisions: 
		1.1
		 |-- 1.1.1
		 |-- 1.1.2
		 |     \-- 1.1.2.1
		 \-- 1.1.3
		
		getFileRevisions(baseRevision = 1.1, scope = SCOPE_LOCAL) returns:
		[ (1.1, 1.1.1), (1.1, 1.1.2), (1.1, 1.1.3) ]
		getFileRevisions(baseRevision = 1.1, scope = SCOPE_SUBTREE) returns:
		[ (1.1, 1.1.1), (1.1, 1.1.2), (1.1.2, 1.1.2.1), (1.1, 1.1.3) ]
		
		Order in returned list does not matter.
		
		@type  filename: string
		@param filename: the filename, relative to the FSB's backend.
		@type  baseRevision: string
		@param baseRevision: the revision from which we ask for branches.
		                     The exact syntax depends on the backend.

		@rtype: list of tuples (string, string)
		@returns: a list of (a, b) where a is the parent revision, and b is a child revision,
		          None for invalid filename or baseRevision.
		"""	
		return None


