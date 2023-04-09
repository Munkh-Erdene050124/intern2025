class NewTrieNode:
    def __init__(self, id, word):
        self.id = id
        self.word = word
        self.state = 0
        self.desc = ''
        self.children = {}

    def to_str(self):
        return '(' + '\n\tid: ' + str(self.id) + '\n\tword: ' + self.word + ',\n\tstate: ' + str(self.state) + ',\n\tdesc: ' + self.desc + ',\n\tchildren: ' + str(len(self.children)) + '\n)'


class NewTrie(object):
    def __init__(self):
        self.root = NewTrieNode([-1], "")

    def insert(self, multword, id):
        node = self.root
        found = self.is_found_mwe(multword)
        if found != None:
            for wrd in multword.split(" "):
                node = node.children[wrd]
            if node.id[len(node.id) - 1] == -2:
                node.id.pop()
            node.id.append(id)
            node.state = 1
        else:
            for wrd in multword.split(" "):
                if wrd not in node.children:
                    node.children[wrd] = NewTrieNode([-2], wrd)
                node = node.children[wrd]
            node.id = [id]
            node.state = 2

    def search(self, words):
        node = self.root
        t_node_list = []
        i = 0
        while i < len(words):
            x_word = words[i].lower().strip()
            if x_word in node.children:
                node = node.children[x_word]
                i += 1
            else:
                if node.id[0] != -2 and (node.state == 2 or node.state == 1):
                    t_node_list.append({'id': node.id, 'idx': i - 1})

                if node.id[0] == -1:
                    i += 1
                else:
                    node = self.root
        return t_node_list

    def is_found_mwe(self, mwe):
        return self._find_mwe(self.root, mwe)

    def _find_mwe(self, node, mwe):
        for word in mwe.split(' '):
            if word not in node.children:
                return None
            node = node.children[word]
        return node

    def is_found_word(self, word):
        return self._find_node(self.root, word)

    def _find_node(self, root, word):
        if root is None:
            return None
        if root.word == word:
            return root
        for child in root.children:
            node = self._find_node(root.children[child], word)
            if node:
                return node
        return None

    def _node_mwe(self, node, prefix):
        for word in sorted(node.children):
            self._print_helper(
                node.children[word], prefix + " " + (word + "-" + str(node.id)))

    def print_trie(self, state=2):
        self._print_helper(self.root, state, "")

    def _print_helper(self, node, state, prefix):
        if node.state == state:
            print(prefix[1:])
        for word in sorted(node.children):
            self._print_helper(
                node.children[word], state, prefix + ' ' + (word + "-" + str(node.children[word].id)))
