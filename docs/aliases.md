## Assigning URL aliases to nodes

In `create` tasks, you can assign URL aliases to nodes by adding the `url_alias` field to you CSV file, like this:

```
file,title,field_description,url_alias
IMG_1410.tif,Small boats in Havana Harbour,Some are blue.,/havana_boats
IMG_2549.jp2,Manhatten Island,Manhatten is part of New York City.,/manhatten
```

You can also assign URL aliases in `update` tasks:

```
node_id,url_alias
345,/this_is_a_cool_item
367,/soisthisone
```

No other configuration is required. URL aliases must start with a forward slash (`/`). When you run Workbench with its `--check` option, it will check whether each alias starts with this character, and whether the alias already exists.
