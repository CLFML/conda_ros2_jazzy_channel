import os
import sys
import requests
import subprocess
from pathlib import Path
import shutil

GH_PAGES_DIR = "gh-pages-repo"

def get_current_version(pkg_name):
    version_file = f"PKG_VERSIONS/{pkg_name}.txt"
    os.makedirs("PKG_VERSIONS", exist_ok=True)
    if not os.path.exists(version_file):
        return None
    with open(version_file) as f:
        return f.readline().strip()

def get_latest_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data["tag_name"], data["assets"]

def download_and_rename(asset_url, dest_path):
    print(f"Downloading: {asset_url}")
    r = requests.get(asset_url)
    r.raise_for_status()
    with open(dest_path, 'wb') as f:
        f.write(r.content)

def update_version_file(pkg_name, version):
    os.makedirs("PKG_VERSIONS", exist_ok=True)
    with open(f"PKG_VERSIONS/{pkg_name}.txt", "w") as f:
        f.write(version + "\n")




def clone_gh_pages(repo):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set!")

    repo_url = f"https://x-access-token:{token}@github.com/{repo}.git"
    subprocess.run(["git", "clone", "--branch", "pages", repo_url, GH_PAGES_DIR], check=True)


def copy_files_to_gh_pages(pkg_name, version):
    linux_src_dir = "pkgs/linux-64"
    win_src_dir = "pkgs/win-64"
    linux_dst = f"{GH_PAGES_DIR}/linux-64/"
    win_dst = f"{GH_PAGES_DIR}/win-64/"
    
    os.makedirs(linux_dst, exist_ok=True)
    os.makedirs(win_dst, exist_ok=True)

    if os.path.exists(linux_src):
        shutil.copy2(linux_src, linux_dst)
    if os.path.exists(win_src):
        shutil.copy2(win_src, win_dst)
    os.chdir(GH_PAGES_DIR)
    subprocess.run(["conda", "index", "."])
    os.chdir("..")


def commit_to_gh_pages(pkg_name, version):
    os.chdir(GH_PAGES_DIR)
    subprocess.run(["git", "config", "user.name", "github-actions"])
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"])
    subprocess.run(["git", "add", "linux-64", "win-64"])
    subprocess.run(["git", "commit", "-m", f"Add {pkg_name} {version} packages"])
    subprocess.run(["git", "push"])
    os.chdir("..")
    
def commit_pkg_versions(pkg_name, version):
    subprocess.run(["git", "config", "user.name", "github-actions"])
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"])
    subprocess.run(["git", "add", f"PKG_VERSIONS/{pkg_name}.txt"])
    subprocess.run(["git", "commit", "-m", f"Update version metadata for {pkg_name} to {version}"])
    subprocess.run(["git", "push"])

def main():
    if len(sys.argv) < 3:
        print("Usage: python check_release.py <package_name> <repo>")
        sys.exit(1)

    pkg_name = sys.argv[1]
    repo = sys.argv[2]

    current_version = get_current_version(pkg_name)
    latest_version, assets = get_latest_release(repo)

    if latest_version == current_version:
        print(f"{pkg_name} is up to date.")
        return

    print(f"New version for {pkg_name}: {latest_version}")
    linux_asset = None
    windows_asset = None

    for asset in assets:
        name = asset['name']
        if name.startswith(pkg_name) and name.endswith('.tar.bz2') and '-win' not in name:
            linux_asset = asset['browser_download_url']
        elif name.startswith(pkg_name) and name.endswith('-win.tar.bz2'):
            windows_asset = asset['browser_download_url']

    Path("pkgs/linux-64").mkdir(parents=True, exist_ok=True)
    Path("pkgs/win-64").mkdir(parents=True, exist_ok=True)

    if linux_asset:
        linux_filename = Path(linux_asset).name
        linux_dest = f"pkgs/linux-64/{linux_filename}"
        download_and_rename(linux_asset, linux_dest)

    if windows_asset:
        win_filename = Path(windows_asset).name.replace("-win.tar.bz2", ".tar.bz2")
        win_dest = f"pkgs/win-64/{win_filename}"
        download_and_rename(windows_asset, win_dest)

    update_version_file(pkg_name, latest_version)
    clone_gh_pages("CLFML/conda_ros2_jazzy_channel")
    copy_files_to_gh_pages(pkg_name, latest_version)
    commit_to_gh_pages(pkg_name, latest_version)
    commit_pkg_versions(pkg_name, latest_version)


if __name__ == "__main__":
    main()
