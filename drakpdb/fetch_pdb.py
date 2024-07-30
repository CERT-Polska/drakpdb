import os

import requests
from requests import HTTPError
from tqdm import tqdm


def fetch_pdb(pdbname, guidage, destdir="."):
    url = "https://msdl.microsoft.com/download/symbols/{}/{}/{}".format(
        pdbname, guidage.lower(), pdbname
    )

    try:
        with requests.get(url, stream=True) as res:
            res.raise_for_status()
            total_size = int(res.headers.get("content-length", 0))
            dest = os.path.join(destdir, os.path.basename(pdbname))

            with tqdm(total=total_size, unit="iB", unit_scale=True) as pbar:
                with open(dest, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 8):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

        return dest
    except HTTPError as e:
        print("Failed to download from: {}, reason: {}".format(url, str(e)))

    raise RuntimeError("Failed to fetch PDB")
