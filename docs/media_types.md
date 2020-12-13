## Setting media types

By default Workbench defines the following file extention to media type mapping:

| File extensions | Media type |
| --- | --- |
| png, gif, jpg, jpeg | image |
| pdf, doc, docx, ppt, pptx | document |
| tif, tiff, jp2, zip, tar | file |
| mp3, wav, aac | audio |
| mp4 | video |
| txt | extracted_text |

If you need to override this default mappping, you can do so in two ways:

1. For all media being created, via the `media_type` (singluar) configuration option. If this is present (for example `media_type: document`), all media created by Workbench will be assigned that media type. Use this option if all of the files in your batch are to be assigned the same media type, but their extensions are not defined in the default mapping.
1. On a per file extension basis, via a mapping in the `media_types` (plural) option in your configuration file like this one:

   ```
   media_types:
    - video: ['mp4', 'ogg']
   ```
   Use this option if all of the files in your batch are not to be assigned the same media type, and their extensions are not defined in the default mapping (or are in addition to the extensions in the default mapping, as in this example).

Note that:

* If a file's extension is not defined in either the default mapping, or in the `media_type` or `media_types` configuration options, the media is assigned the `file` type.
* If you use the `media_types` configuration option, your mapping replaces all of Workbench's default mappings. However, you may include multiple entries, e.g.:
   ```
   media_types:
    - video: ['mp4', 'ogg']
    - image: ['png', 'gif', 'jpg', 'jpeg']
   ```
* If both `media_type` and `media_types` are included in the config file, the mapping is ignored and the media type assigned in `media_type` is used.
