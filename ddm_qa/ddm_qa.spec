from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_dir = Path(SPECPATH)


# Collect complete package contents for packages that rely on
# compiled extensions, plugins and package data.
rasterio_datas, rasterio_binaries, rasterio_hiddenimports = collect_all(
    "rasterio"
)

matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all(
    "matplotlib"
)

scipy_datas, scipy_binaries, scipy_hiddenimports = collect_all(
    "scipy"
)


datas = (
    rasterio_datas
    + matplotlib_datas
    + scipy_datas
)

binaries = (
    rasterio_binaries
    + matplotlib_binaries
    + scipy_binaries
)

hiddenimports = (
    rasterio_hiddenimports
    + matplotlib_hiddenimports
    + scipy_hiddenimports
)


a = Analysis(
    [str(project_dir / "ddm_qa_cli.py")],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(project_dir / "pyinstaller_runtime.py"),
    ],
    excludes=[],
    noarchive=False,
)


pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ddm_qa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)