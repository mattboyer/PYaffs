class FSLeaf(object):
    def __init__(self, filesystem, header):
        self._filesystem = filesystem

        self.inode = header.objectid
        self.parent = header.parent_objid
        self.name = header.name

        self.mode = header.mode % 0o1000
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
            fs_obj = self._filesystem.get_obj_from_inode(fs_obj.parent)

        return '/' + '/'.join(path_tokens[::-1])

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

    def read(self):
        return self._filesystem.get_file_bytes(self.inode)

class FSDir(FSLeaf):
    def __init__(self, filesystem, header):
        FSLeaf.__init__(self, filesystem, header)
        # Populate dir entries
        self.entries = list()

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __contains__(self, leaf_name):
        for leaf in iter(self):
            if leaf_name == leaf.name:
                return True
        return False

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

    def get_leaf(self, leaf_name):
        if not leaf_name in self:
            # Should we raise something instead?
            return None
        for leaf in self:
            if leaf_name == leaf.name:
                return leaf

class FileSystem(object):
    def __init__(self, dumper):
        self.root_inode = None
        self.root_object = None
        self._parents = dict()
        self._inodes = dict()

        self.dumper = dumper

        self._build_fs(self.dumper.headers)

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
                    dir_object.entries.append(inode_obj)
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

    def get_obj_from_inode(self, inode):
        return self._inodes[inode]

    def get_obj_from_path(self, path):
        path_tokens = path.split('/')[1:]
        if not 1 <= len(path_tokens) or '' in path_tokens:
            raise ValueError("Malformed path {0}".format(path))

        search_dir = self.root_object
        for idx, token in enumerate(path_tokens):
            leaf = search_dir.get_leaf(token)
            if idx < len(path_tokens) - 1:
                assert isinstance(leaf, FSDir), leaf
                search_dir = leaf
            else:
                return leaf

    def find(self, obj_type, name):

        matches = set()
        for obj in self._inodes.values():
            if not isinstance(obj, obj_type):
                continue

            if name != obj.name:
                continue

            matches.add(obj)

        return matches

    def get_file_bytes(self, inode):
        matches = list()
        for idx, spare in enumerate(self.dumper.spares):
            if inode == spare.objectid and 0 != spare.chunkid:
                matches.append((idx, spare))

        # Let's order these matches according to their chunkid
        matches.sort(key=lambda s:s[1].chunkid)
        assert len(matches) == matches[-1][1].chunkid

        data = bytes()
        for idx, spare in matches:
            data += self.dumper.read_block_data(idx)

        return data
