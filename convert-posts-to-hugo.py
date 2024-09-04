#!/usr/bin/env python3

# this scripts performs a first rough conversion from Grav to Hugo.
# this is not meant to be an automatic tool: after the conversion, every post needs a thorough manual review.

import os
import shutil
import sys
from datetime import datetime

def process_directory(directory):
    # Create 'images' subdirectory if it doesn't exist
    images_dir = os.path.join(directory, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    # Move .jpg and .png files to 'images' subdirectory
    for file_name in os.listdir(directory):
        if file_name.endswith('.jpg') or file_name.endswith('.png'):
            shutil.move(os.path.join(directory, file_name), os.path.join(images_dir, file_name))

    # Rename 'item.md' to 'index.md'
    item_md_path = os.path.join(directory, 'item.md')
    index_md_path = os.path.join(directory, 'index.md')
    if os.path.exists(item_md_path):
        os.rename(item_md_path, index_md_path)

    # Process 'index.md' file
    if os.path.exists(index_md_path):
        with open(index_md_path, 'r') as file:
            lines = file.readlines()

        with open(index_md_path, 'w') as file:
            in_front_matter = False
            for line in lines:
                if line.strip() == '---':
                    in_front_matter = not in_front_matter
                    file.write(line)
                    continue

                if in_front_matter:
                    # Process date line
                    if line.startswith('date:'):
                        date_str = line.split(' ')[1].strip().strip("'")
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        new_date_str = date_obj.strftime('publishDate: \'%Y-%m-%dT09:00:00+01:00\'')
                        file.write(new_date_str + '\n')
                        continue

                    # Remove taxonomy line
                    if line.startswith('taxonomy:'):
                        continue

                    # Replace category with categories
                    line = line.replace('category:', 'categories:')

                    # Replace tag with tags
                    line = line.replace('tag:', 'tags:')

                    # Replace hero_image with image
                    line = line.replace('hero_image:', 'image:')

                    # Remove lines containing hero_, feed:, limit:
                    if any(keyword in line for keyword in ['hero_', 'feed:', 'limit:']):
                        continue

                    # Add slug line below title
                    if line.startswith('title:'):
                        file.write(line)
                        file.write('slug: \n')
                        continue

                file.write(line)

if __name__ == "__main__":
    for directory in sys.argv[1:]:
        process_directory(directory)

