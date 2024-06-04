import http.client
import json
import time
import traceback
import urllib.request
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Asset(object):
    name: str
    keywords: str
    url: str
    size: int


def get_assets():
    api = (
        "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest"
    )
    req = urllib.request.Request(api, headers={"User-Agent": "Chrome"})
    with urllib.request.urlopen(url=req, timeout=10) as resp:
        data = json.loads(resp.read())
        # print(data)
        urls = [
            Asset(
                i["name"],
                [k.replace(f"+{data['name']}", "") for k in i["name"].split("-", 6)],
                i["browser_download_url"],
                i["size"],
            )
            for i in data["assets"]
            if not i["name"].endswith(".sha256") and i["name"].count("-") >= 6
        ]
        return urls


def get_time():
    return time.strftime("%H:%M:%S")


def download_python():
    """Download python portable interpreter from https://github.com/indygreg/python-build-standalone/releases. `python -m morebuiltins.download_python`

    λ python -m morebuiltins.download_python
    [10:56:17] Checking https://api.github.com/repos/indygreg/python-build-standalone/releases/latest
    [10:56:19] View the rules:
    https://gregoryszorc.com/docs/python-build-standalone/main/running.html#obtaining-distributions

    [10:56:19] Got 290 urls from github.

    [290] Enter keywords (can be int index or partial match, defaults to 0):
    0. windows
    1. linux
    2. darwin
    0
    [10:56:24] Filt with keyword: "windows". 290 => 40

    [40] Enter keywords (can be int index or partial match, defaults to 0):
    0. 3.12.3
    1. 3.11.9
    2. 3.10.14
    3. 3.9.19
    4. 3.8.19

    [10:56:25] Filt with keyword: "3.12.3". 40 => 8

    [8] Enter keywords (can be int index or partial match, defaults to 0):
    0. x86_64
    1. i686

    [10:56:28] Filt with keyword: "x86_64". 8 => 4

    [4] Enter keywords (can be int index or partial match, defaults to 0):
    0. shared-pgo-full.tar.zst
    1. shared-install_only.tar.gz
    2. pgo-full.tar.zst
    3. install_only.tar.gz
    3
    [10:56:33] Filt with keyword: "install_only.tar.gz". 4 => 1
    [10:56:33] Download URL: 39.1 MB
    https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3%2B20240415-x86_64-pc-windows-msvc-install_only.tar.gz
    File path to save(defaults to `./cpython-3.12.3+20240415-x86_64-pc-windows-msvc-install_only.tar.gz`)?
    or `q` to exit.

    [10:56:38] Start downloading...
    https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3%2B20240415-x86_64-pc-windows-msvc-install_only.tar.gz
    D:\github\morebuiltins\morebuiltins\download_python\cpython-3.12.3+20240415-x86_64-pc-windows-msvc-install_only.tar.gz
    [10:56:44] Downloading: 39.12 / 39.12 MB | 100.00% | 11.3 MB/s | 0s
    [10:56:44] Download complete."""
    print(
        f"[{get_time()}] Checking https://api.github.com/repos/indygreg/python-build-standalone/releases/latest",
        flush=True,
    )
    assets = get_assets()
    print(
        f"[{get_time()}] View the rules:\nhttps://gregoryszorc.com/docs/python-build-standalone/main/running.html#obtaining-distributions\n",
        flush=True,
    )
    print(f"[{get_time()}] Got {len(assets)} urls from github.")

    def sort_key(s):
        try:
            return tuple(map(int, s.split(".")))
        except ValueError:
            return s

    indexs = [4, 1, 5, 2, 3, 0, 6]
    for index in indexs:
        try:
            to_filt = sorted(
                {i.keywords[index] for i in assets}, key=sort_key, reverse=True
            )
        except IndexError:
            continue
        if len(to_filt) == 1:
            continue
        choices = "\n".join((f"{idx}. {ii}" for idx, ii in enumerate(to_filt, 0)))
        arg = input(
            f"\n[{len(assets)}] Enter keywords (can be int index or partial match, defaults to 0):\n{choices}\n"
        )
        if not arg:
            arg = to_filt[0]
        elif arg.isdigit():
            arg = to_filt[int(arg)]
        old = len(assets)
        temp = [i for i in assets if arg == i.keywords[index]]
        if temp:
            assets = temp
        else:
            assets = [i for i in assets if arg in i.keywords[index]]
        print(
            f'[{get_time()}] Filt with keyword: "{arg}".',
            old,
            "=>",
            len(assets),
            flush=True,
        )
    while len(assets) > 1:
        names = "\n".join(i.name for i in assets)
        arg = input(f"Enter keyword to reduce the list (partial match):\n{names}\n")
        assets = [i for i in assets if arg in i.name]
    if not assets:
        input("No match, press enter to exit.")
        return
    asset = assets[0]
    download_url = asset.url
    total_size = asset.size
    print(
        f"[{get_time()}] Download URL:",
        round(total_size / 1024**2, 1),
        "MB",
    )
    print(download_url, flush=True)
    target = (
        input(
            f"File path to save(defaults to `./{asset.name}`)?\nor `q` to exit.\n"
        ).lower()
        or asset.name
    )
    if target == "q":
        return
    target_path = Path(target)
    try:
        target_path.unlink()
    except FileNotFoundError:
        pass
    print(f"[{get_time()}] Start downloading...")
    print(download_url)
    print(target_path.absolute(), flush=True)
    records = deque(maxlen=1000)

    def reporthook(blocknum, blocksize, totalsize):
        if totalsize < 0:
            totalsize = total_size
        _done = blocknum * blocksize
        if not _done:
            return
        percent = 100.0 * _done / totalsize
        total = totalsize / 1024 / 1024
        done = _done / 1024 / 1024 or total
        if percent > 100:
            percent = 100
        now = time.time()
        record = (now, _done)
        records.appendleft(record)
        timeleft = "-"
        _speed = 0
        if len(records) >= 2:
            for record in records:
                if now - record[0] > 1:
                    break
            time_diff = now - record[0]
            if time_diff:
                _speed = round((_done - record[1]) / time_diff, 1)
                secs = (totalsize - _done) / _speed
                if secs > 60:
                    timeleft = f"{int(secs / 60)}:{int(secs % 60):02}"
                else:
                    timeleft = f"{int(secs)}s"
        if _speed > 1024**2:
            speed = f"{round(_speed / 1024**2, 1)} MB/s"
        elif _speed > 1024:
            speed = f"{round(_speed / 1024, 1)} KB/s"
        else:
            speed = f"{round(_speed, 1)} B/s"
        print(
            f"[{get_time()}] Downloading: {done:.2f} / {total:.2f} MB | {percent:.2f}% | {speed} | {timeleft} {' ' * 10}",
            end="\r",
            flush=True,
        )

    temp_path = target_path.with_suffix(".tmp")
    for _ in range(3):
        try:
            urllib.request.urlretrieve(
                download_url, temp_path.absolute().as_posix(), reporthook=reporthook
            )
            temp_path.rename(target_path)
            print(
                f"\n[{get_time()}] Download complete.",
                flush=True,
            )
            break
        except http.client.RemoteDisconnected:
            continue
        except KeyboardInterrupt:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            print()
            print(f"\n[{get_time()}] Download canceled.", flush=True)
            return
        except Exception:
            print()
            traceback.print_exc()
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            break
    print("Press enter to exit.", flush=True)
    input()


if __name__ == "__main__":
    download_python()
