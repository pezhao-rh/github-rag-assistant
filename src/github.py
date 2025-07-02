import subprocess
import os
import shutil
import fnmatch
from typing import Optional

class Node:
    """Node class for representing structure of github repositories."""
    
    def __init__(self, filepath: str, is_dir: bool = False, parent: Optional['Node'] = None):
        """Initialize a new Node.
        
        Args:
            filepath: Path to the file or directory
            is_dir: Whether this node represents a directory
            parent: Parent node in the tree
        """
        self.name = os.path.basename(filepath)
        self.filepath = filepath
        self.is_dir = is_dir
        self.parent = parent
        self.children = [] if is_dir else None

    def add_child(self, child_node: 'Node'):
        """Add a child node and maintain sorted order.
        
        Args:
            child_node: Child node to add
        """
        if self.children:
            self.children.append(child_node)
            child_node.parent = self
            self.children.sort(key=lambda x: x.name.lower())

def build_tree(root_path: str) -> Optional[Node]:
    """Build a tree of file nodes from a root directory path.
    
    Args:
        root_path: Path to the root directory
        
    Returns:
        Root node of the tree, or None if path doesn't exist
    """
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


def isIgnored(filepath: str) -> bool:
    """Check if a file should be ignored for ingestion.
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        True if file should be ignored, False otherwise
    """
    filename = os.path.basename(filepath)
    patterns = [
        # Python
        '*.pyc','*.pyo','*.pyd','__pycache__','.pytest_cache','.coverage','.tox','.nox','.mypy_cache','.ruff_cache','.hypothesis','poetry.lock','Pipfile.lock','init.py','__init__.py','.python-version','uv.lock','pyproject.toml',
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
        'LICENSE','.helmignore','*.pdf','*.csv','.ansible-lint',
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

def get_file_list(root_node: Node) -> list[str]:
    """Create a list of file paths from a tree structure.
    
    Args:
        root_node: Root node of the tree to traverse
        
    Returns:
        List of file paths
    """
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

def generate_diagram(root_node: Node) -> str:
    """Generate a markdown visualization of a file tree.
    
    Args:
        root_node: Root node of the tree to visualize
        
    Returns:
        Markdown-formatted string representation of the tree
    """
    lines = []

    def traverse_and_format(node: Node, level: int = 0, prefix: str = ""):

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


def clone_repository(link: str) -> str:
    """Clone a git repository and return its local path.
    
    Args:
        link: Git repository URL to clone
        
    Returns:
        Path to the cloned repository directory
    """
    repo_name = link.split('/')[-1]
    repo_name = repo_name.replace('.git', '')
    try:
        subprocess.run(['git', 'clone', link], check=True)
        filepath = os.path.join(os.getcwd(), repo_name)
        print(f'Successfully cloned repository to: {filepath}')
        return filepath
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")
        return ""


def delete_repository(filepath: str) -> None:
    """Delete a repository directory.
    
    Args:
        filepath: Path to the repository directory to delete
    """
    if not os.path.exists(filepath):
        print("Repository does not exist")
    try:
        shutil.rmtree(filepath)
        print("Repository deleted")
    except Exception as e:
        print(f"Error deleting repository: {e}")
    
def clone_and_build_tree(link: str) -> tuple[str, list[str], str]:
    """Clone a repository and build its file tree structure.
    
    Args:
        link: Git repository URL to clone
        
    Returns:
        Tuple of (root_path, file_list, diagram) where:
        - root_path: Path to cloned repository
        - file_list: List of file paths in the repository
        - diagram: Markdown visualization of the tree structure
        
    Raises:
        ValueError: If tree building fails
    """
    
    root_path = clone_repository(link)
    root_node = build_tree(root_path)
    if root_node is None:
        raise ValueError("Failed to build tree")
    
    file_list = get_file_list(root_node)
    diagram = generate_diagram(root_node)

    return root_path, file_list, diagram