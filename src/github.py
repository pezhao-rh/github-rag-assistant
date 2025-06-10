import subprocess
import os
from collections import deque
import shutil
import fnmatch

# Node class for representing structure of github repositories
class Node:
    def __init__(self, filepath, is_dir=False, parent=None):
        self.name = os.path.basename(filepath)
        self.filepath = filepath
        self.is_dir = is_dir
        self.parent = parent
        self.children = [] if is_dir else None

    def add_child(self, child_node):
        self.children.append(child_node)
        child_node.parent = self
        self.children.sort(key=lambda x: x.name.lower())


def build_tree(root_path):
    # build tree of file nodes given the path of root
    if not os.path.exists(root_path):
        return None
    if os.path.isfile(root_path):
        return Node(root_path, is_dir=False)
    
    root_node = Node(root_path, is_dir=True)
    node_map = {root_path: root_node}

    for root, dirs, files in os.walk(root_path):
        parent_node = node_map.get(root)
        if parent_node is None:
            continue

        # filter out ignored files
        dirs[:] = [d for d in dirs if not isIgnored(d)]
        files[:] = [f for f in files if not isIgnored(f)]

        # add nodes
        for d in dirs:
            dir_path = os.path.join(root, d)
            dir_node = Node(dir_path, is_dir=True)
            parent_node.add_child(dir_node)
            node_map[dir_path] = dir_node

        for f in files:
            file_path = os.path.join(root, f)
            file_node = Node(file_path)
            parent_node.add_child(file_node)

    return root_node


def isIgnored(filepath):
    filename = os.path.basename(filepath)
    # if file should be ignored for ingestion
    patterns = [
        # Python
        '*.pyc','*.pyo','*.pyd','__pycache__','.pytest_cache','.coverage','.tox','.nox','.mypy_cache','.ruff_cache','.hypothesis','poetry.lock','Pipfile.lock','init.py','__init__.py',
        # JavaScript/FileSystemNode
        'node_modules','bower_components','package-lock.json','yarn.lock','.npm','.yarn','.pnpm-store','bun.lock','bun.lockb',
        # Java'*.class',
        '*.jar','*.war','*.ear','*.nar','.gradle/','build/','.settings/','.classpath','gradle-app.setting','*.gradle',
        # IDEs and editors / Java
        '.project',
        # C/C++
        '*.o','*.obj','*.dll','*.dylib','*.exe','*.lib','*.out','*.a','*.pdb',
        # Swift/Xcode
        '.build/','*.xcodeproj/','*.xcworkspace/','*.pbxuser','*.mode1v3','*.mode2v3','*.perspectivev3','*.xcuserstate','xcuserdata/','.swiftpm/',
        # Ruby
        '*.gem','.bundle/','vendor/bundle','Gemfile.lock','.ruby-version','.ruby-gemset','.rvmrc',
        # Rust
        'Cargo.lock','**/*.rs.bk',
        # Java / Rust
        'target/',
        # Go
        'pkg/',
        # .NET/C//
        'obj/','*.suo','*.user','*.userosscache','*.sln.docstates','packages/','*.nupkg',
        # Go / .NET / C//
        'bin/',
        # Version control
        '.git','.svn','.hg','.gitignore',
        # Virtual environments
        'venv','.venv','env','virtualenv',
        # Temporary and cache files
        '*.log','*.bak','*.swp','*.tmp','*.temp','.cache','.sass-cache','.eslintcache','.DS_Store','Thumbs.db','desktop.ini','.vscode',
        # Build directories and artifacts
        'build','dist','target','out','*.egg-info','*.egg','*.whl','*.so',
        # Documentation
        'site-packages','.docusaurus','.next','.nuxt',
        # Other common patterns
        'LICENSE','.helmignore','*.pdf','*.csv',
        # Zip files
        '*.tar','*.zip','*.tar.gz','*.tar.xz','*.tar.bz2',
        # Minified files
        '*.min.js','*.min.css',
        # Source maps
        '*.map',
        # Terraform
        '.terraform','*.tfstate*',
        # Images
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff', '*.webp', '*.svg', '*.ico','img'
    ]

    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


def get_file_list(root_node):
    # list of files to ingest from a full tree
    files = []
    stack = [root_node]
    while stack:
        node = stack.pop()
        if not node.is_dir:
            files.append(node.filepath)
        elif node.children:
            for child in node.children:
                stack.append(child)
    return files

def generate_diagram(root_node):
    # generating visual representation of tree
    if root_node is None:
        return "No directory to display."

    lines = []

    def traverse_and_format(node, level=0, prefix=""):

        filename = node.name
        if node.is_dir:
            filename = f"**{filename}**" 

        line = f"{prefix}{filename}"
        lines.append(line)

        if node.is_dir and node.children:

            # add each child
            for i, child in enumerate(node.children):
                
                is_last_child = (i == len(node.children) - 1)
                connector = "└── " if is_last_child else "├── "
                traverse_and_format(child, level + 1, prefix + connector)

    traverse_and_format(root_node)

    return "  \n".join(lines)


def clone_repository(link):
    # clone repository, return path of repo
    repo_name = link.split('/')[-1]
    repo_name = repo_name.replace('.git', '')
    try:
        subprocess.run(['git', 'clone', link], check=True)
        filepath = os.path.join(os.getcwd(), repo_name)
        print(f'Successfully cloned repository to: {filepath}')
        return filepath
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")


def delete_repository(filepath):
    if not os.path.exists(filepath):
        print("Repository does not exist")
        return False
    try:
        shutil.rmtree(filepath)
        print("Repository deleted")
        return True
    except Exception as e:
        print(f"Error deleting repository: {e}")
        return False
    

def clone_and_build_tree(link):
    # clones repository and returns root path, file list, and markdown visualization
    root_path = clone_repository(link)
    root_node = build_tree(root_path)
    file_list = get_file_list(root_node)
    diagram = generate_diagram(root_node)

    return root_path, file_list, diagram

def main():
    root_path = clone_repository('https://github.com/rh-ai-kickstart/AI-Observability-Metric-Summarizer.git')
    root_node = build_tree(root_path)
    markdown = generate_diagram(root_node)
    print(markdown)
    # root_path = '/Users/pezhao/Documents/Testing/github-rag-assistant/RAG-Blueprint'
    # delete_repository(root_path)
    # shutil.rmtree('.chroma')


if __name__ == "__main__":
    main()
