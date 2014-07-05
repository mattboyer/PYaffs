import os

class FSLeaf(object):
    def __init__(self, filesystem, header):
        self._filesystem = filesystem

        self.inode = header.objectid
        self.parent = header.parent_objid
        self.name = header.name

        self.mode = header.mode
        self.uid = header.uid
        self.gid = header.gid
        self.atime = header.atime
        self.mtime = header.mtime
        self.ctime = header.ctime

    @property
    def path(self):
        path_tokens = list()
        fs_obj = self
        while fs_obj.parent != fs_obj.inode:
            path_tokens.append(fs_obj.name)
            fs_obj = self._filesystem.get_inode(fs_obj.parent)

        return os.path.sep + os.path.join('', *path_tokens[::-1])

    @property
    def perms(self):
        return "uid:gid {0}:{1} mode {2}".format(self.uid, self.gid, self.mode)

class FSFile(FSLeaf):
    def __init__(self, filesystem, header):
        FSLeaf.__init__(self, filesystem, header)
        self.size = header.size
        # TODO Do something about the actual *DATA*!!!!

    def __len__(self):
        return self.size

    def __repr__(self):
        return "<File {p} {s} bytes {perms} inode {i}>".format(
                p=self.path,
                s=len(self),
                perms=self.perms,
                i=self.inode,
            )

class FSDir(FSLeaf):
    def __init__(self, filesystem, header):
        FSLeaf.__init__(self, filesystem, header)
        # Populate dir entries
        self.entries = set()

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __repr__(self):
        return "<Dir {p} {s} entries {perms} inode {i}>".format(
                p=self.path,
                s=len(self),
                perms=self.perms,
                i=self.inode,
            )

    def walk(self):
        print(self)

        ordered_entries = list(self.entries)
        ordered_entries.sort(key=lambda x:x.name)
        for entry in ordered_entries:
            if not isinstance(entry, FSDir):
                print(entry)
            else:
                entry.walk()

class FileSystem(object):
    def __init__(self, headers_dict):
        self.root_inode = None
        self.root_object = None
        self._parents = dict()
        self._inodes = dict()

        self._build_fs(headers_dict)

        if not (self.root_object):
            raise Exception("Could not build FS")


    def _build_fs(self, headers):
        def _build_objects_in_dir(dir_object):
            if dir_object.parent not in self._parents:
                raise IOError("{0} not a dir".format(dir_inode))

            for child_inode in self._parents[dir_object.inode]:
                child_header = headers[child_inode]

                #print(child_header.name)
                inode_obj = None
                if 1 == child_header.object_type:
                    # We have a regular file
                    inode_obj = FSFile(self, child_header)
                if 3 == child_header.object_type:
                    # We have a dir
                    inode_obj = FSDir(self, child_header)
                    _build_objects_in_dir(inode_obj)

                if inode_obj:
                    dir_object.entries.add(inode_obj)
                    self._inodes[inode_obj.inode] = inode_obj

        for header_objid, header in headers.items():
            if not header.parent_objid in headers:
                raise IOError("Object {0}'s parent objectid {1} not found".format(repr(header), header.parent_objid))

            parent = headers[header.parent_objid]
            if parent == header:
                # We've found the root, what do we do?
                self.root_inode = header_objid
                continue

            #print("{0} has child {1}".format(repr(parent), repr(header)))
            if not header.parent_objid in self._parents:
                self._parents[header.parent_objid] = set([header_objid])
            else:
                self._parents[header.parent_objid].add(header_objid)

        if not self.root_inode:
            raise IOError("Root inode not found")

        self.root_object = FSDir(self, headers[self.root_inode])
        self._inodes[self.root_inode] = self.root_object
        _build_objects_in_dir(self.root_object)

    def get_inode(self, inode):
        return self._inodes[inode]

    def find(self, obj_type, name):

        matches = set()
        for obj in self._inodes.values():
            if not isinstance(obj, obj_type):
                continue

            if name != obj.name:
                continue

            matches.add(obj)

        return matches
