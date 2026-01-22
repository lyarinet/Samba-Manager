#!/usr/bin/env python3


def fix_file():
    with open("app/samba_utils.py", "r") as f:
        content = f.read()

    # Replace the key mappings
    content = content.replace(
        "'force group': 'force_group'\n                    }",
        "'force group': 'force_group',\n                        'max connections': 'max_connections'\n                    }",
    )

    with open("app/samba_utils.py", "w") as f:
        f.write(content)

    print("File updated successfully!")


if __name__ == "__main__":
    fix_file()
