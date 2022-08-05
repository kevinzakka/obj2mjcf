#!/bin/bash
#
# Install V-HACD v4.0.0.

# Check that cmake is installed.
t=`which cmake`
if [ -z "$t" ]; then
  echo "You need cmake to install V-HACD." 1>&2
  exit 1
fi

# Clone and build executable.
git clone https://github.com/kmammou/v-hacd.git --branch v4.0.0
cd v-hacd/app
cmake CMakeLists.txt
cmake --build .

# Add executable to /usr/local/bin.
sudo ln -s "$PWD/TestVHACD" /usr/local/bin/TestVHACD
