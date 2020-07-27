# RegTest Whatsonchain block explorer
When you have success you should see this (note block height=200 because it is on RegTest network):

![ScreenShot](woc-success.png)

# Step 1: Install node.js
Go to: https://nodejs.org/en/
and install node.js version 12 LTS or later 

BUT please leave this box unchecked! 
(we need to configure the npm-gyp python manually in step 2)

![ScreenShot](node.js_extras.png)

# Step 2 (configure npm-gyp for python)

open a terminal window and type:
 
    > npm config set python /path/to/executable/python

# Step 3 (install the whatsonchain explorer package)
Clone this repository and install package: 

    > git clone https://github.com/AustEcon/woc-explorer.git
    > cd woc-explorer
    > npm install
    > npm build

NOTE: I would like to continue using the main repository
at https://github.com/waqas64/woc-explorer at a later date. But this is
a short-term way to have everything pre-configured for our RegTest needs
(removes the step of editing configuration files is all).

Now you can start the explorer with:

    > npm start
    
Webpage is viewable at http://127.0.0.1:3002/

**You need to be running electrumx and the node to have anything to look at.**
> electrumsv-sdk start --ex-node

or ideally run the 'full stack' (electrumsv + electrumx + node):
> electrumsv-sdk start --full-stack 

The docker build for this explorer doesn't work for me at the moment. YMMV.