import argparse
import json
import os
import subprocess
import uuid
from tqdm import tqdm

# C语言解析需要
try:
    from clang.cindex import Index, CursorKind
    CLANG_AVAILABLE = True
except ImportError:
    CLANG_AVAILABLE = False
    print("警告：Clang库未找到，C语言解析功能将不可用。请运行 'pip install libclang'")


def checkout_commit(repo_path, commit_id):
    """Checkout the specified commit in the given local git repository.
    :param repo_path: Path to the local git repository
    :param commit_id: Commit ID to checkout
    :return: None
    """
    try:
        # Change directory to the provided repository path and checkout the specified commit
        print(f"Checking out commit {commit_id} in repository at {repo_path}...")
        subprocess.run(["git", "-C", repo_path, "checkout", commit_id], check=True)
        print("Commit checked out successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running git command: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def clone_repo(repo_name, local_path):
    """克隆一个指定的GitHub仓库到本地。"""
    print(f"Cloning repository from https://github.com/{repo_name}.git to {local_path}...")
    try:
        subprocess.run(["git", "clone", f"https://github.com/{repo_name}.git", local_path], check=True, capture_output=True)
        print("Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running git command: {e.stderr.decode()}")
        exit(1)


def parse_c_file(file_path):
    """
    解析一个C文件，提取结构体、联合体、函数定义及其行号和文本。
    返回一个元组，格式与Python版本的 parse_python_file 保持一致。
    """
    struct_info = []
    function_info = []
    file_lines = []

    if not CLANG_AVAILABLE:
        return struct_info, function_info, file_lines

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
            file_lines = file_content.splitlines()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return [], [], []
        
    try:
        index = Index.create()
        tu = index.parse(file_path, args=['-I/usr/include', '-w'], unsaved_files=[(file_path, file_content)])
        
        for node in tu.cursor.walk_preorder():
            if node.location.file and node.location.file.name == file_path:
                start_line, end_line = node.extent.start.line, node.extent.end.line
                node_text = file_lines[start_line - 1 : end_line]
                
                if node.kind in [CursorKind.STRUCT_DECL, CursorKind.UNION_DECL] and node.is_definition():
                    struct_info.append({
                        "name": node.spelling or "anonymous",
                        "start_line": start_line,
                        "end_line": end_line,
                        "text": node_text
                    })
                elif node.kind == CursorKind.FUNCTION_DECL and node.is_definition():
                    function_info.append({
                        "name": node.spelling,
                        "start_line": start_line,
                        "end_line": end_line,
                        "text": node_text
                    })
    except Exception as e:
        print(f"Clang parsing error in file {file_path}: {e}")

    return struct_info, function_info, file_lines


def create_structure(directory_path):
    """
    通过解析C/H文件来创建仓库目录的结构。
    """
    structure = {}
    
    for root, _, files in os.walk(directory_path):
        if '.git' in root:
            continue
            
        # 为了与Python版本完全一致，我们在这里构建嵌套字典
        relative_root = os.path.relpath(root, directory_path)
        
        curr_struct = structure
        if relative_root != ".":
            for part in relative_root.split(os.sep):
                curr_struct = curr_struct.setdefault(part, {})
        
        for file_name in files:
            if file_name.endswith((".c", ".h")):
                file_path = os.path.join(root, file_name)
                structs, functions, file_lines = parse_c_file(file_path)
                # 这里的字典键名与Python版本保持一致，用 'classes' 对应 'structs'
                curr_struct[file_name] = {
                    "classes": structs, # 用 'classes' 键来存储C的结构体信息
                    "functions": functions,
                    "text": file_lines,
                }
            else:
                curr_struct[file_name] = {}
                
    return structure


def get_project_structure_from_scratch(repo_name, commit_id, instance_id, repo_playground):
    """
    【C语言版】
    与Python版本逻辑完全相同的顶层接口。
    """
    # 1. 创建临时的、带UUID的沙盒文件夹
    temp_playground = os.path.join(repo_playground, str(uuid.uuid4()))
    assert not os.path.exists(temp_playground), f"{temp_playground} already exists"
    os.makedirs(temp_playground)
    
    # 2. 在沙盒中克隆仓库
    local_folder_name = repo_name.split('/')[-1]
    local_repo_path = os.path.join(temp_playground, local_folder_name)
    clone_repo(repo_name, local_repo_path)
    
    # 3. 检出commit
    if not checkout_commit(local_repo_path, commit_id):
        print(f"检出失败，清理并退出对 {instance_id} 的分析。")
        subprocess.run(["rm", "-rf", temp_playground], check=True)
        return None

    # 4. 分析结构
    print("开始分析代码结构...")
    structure = create_structure(local_repo_path)
    
    # 5. 清理沙盒
    print(f"清理临时文件夹: {temp_playground}")
    subprocess.run(["rm", "-rf", temp_playground], check=True)
    
    # 6. 返回与Python版本完全一致的结果
    d = {
        "repo": repo_name,
        "base_commit": commit_id,
        "structure": structure,
        "instance_id": instance_id,
    }
    return d

