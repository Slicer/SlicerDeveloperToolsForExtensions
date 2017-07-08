# SlicerDeveloperToolsForExtensions


## What is it?

This repository contains 3D Slicer extensions that offers different tools to help developers when they develop Slicer extensions:
- Developer Tools For Extensions: It allows one to manually install extensions from an archive (*.zip or *.tar.gz). These archives can either be created locally when one creates their own extensions (this tools can help the developer to verify that their extension is correctly packaged). It can also be convenient to distribute your Slicer extensions on your own website, or privately. It also allows to directly load a scripted module while Slicer is already running.
- Extension Download Statistics: It allows developers to know how many times their extensions have been downloaded.

## Command line interface

The CLI mode allows to collect downloads stats for the specified or all of the
extensions and save the results in CSV or JSON format, from the command line.

Note that you will need to run the script via Slicer using `--python-script` flag
to access this mode.

Example usage:

```
/Applications/Slicer.app/Contents/MacOS/Slicer --disable-cli-modules --no-main-window --no-splash \
  --python-script ~/github/SlicerDeveloperToolsForExtensions/ExtensionStats/ExtensionStats.py \
  -e SlicerRT --output-csv stats.csv --output-json stats.json
```

## License

See License.txt

## More information

More information about Slicer on http://www.slicer.org/
