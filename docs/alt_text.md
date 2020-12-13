## Adding alt text to images

Islandora image media require a value in their "Alternative text" field. This text is used as the `alt` text in the HTML markup rendering the image.

You can assign alt text values by adding the `image_alt_text` field to you CSV file, like this:

```
file,title,field_description,image_alt_text
IMG_1410.tif,Small boats in Havana Harbour,They are nice boats.Small boats in Havana Harbour.
IMG_2549.jp2,Manhatten Island,It was windy that day.Picture of Manhatten Island.
```

The value will only be applied to image media. If you do not include this field in your CSV file, Workbench will use the node's title as the alt text. Note that Workbench strips out all HTML markup within the alt text. Also note that this feature is only available in the `create` task.
