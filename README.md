# whatsapp_bot_gemini

This project implements a WhatsApp bot capable of generating AI responses to user queries using the Gemini API. It leverages the Flask framework to handle incoming requests and responses.

geminiai prompting guide: https://services.google.com/fh/files/misc/gemini-for-google-workspace-prompting-guide-101.pdf

## Full Documentation
For detailed documentation, including deployment instructions and further customization options, please refer to this medium article. [https://medium.com/@yousseftarhri15/building-an-intelligent-whatsapp-chatbot-with-gemini-llm-a-step-by-step-guide-to-deployment-on-e66d95035314]

### Gowshi experiment
python version 3.12
venv version 3.12
    -sudo apt update
    -sudo apt install software-properties-common  #Install the required dependencies for adding new repositories:
    -sudo add-apt-repository ppa:deadsnakes/ppa   #The Deadsnakes PPA contains newer Python versions for Ubuntu. Add it using the following 
    -sudo apt update
    -sudo apt install python3.12-venv
    -python3.12 -m venv dtvenv

### How to run
Update ACCESS_TOKEN taken from meta in .env file

"/home/senzmatepc27/Desktop/senzmate/Internal projects/my_gemini_bot/bin/python" "/home/senzmatepc27/Desktop/senzmate/Internal projects/whatsapp_bot_gemini/run.py"

Do port forwarding using vscode: https://code.visualstudio.com/docs/editor/port-forwarding 
Make sure to set the visibility "public"

Configure the port forwarded URL in Meta->whatsapp->Configuration->callback URL

Now send text msg in whatsapp and get a reply



NOTE:
meta for developers: https://developers.facebook.com/apps/442432191997596/whatsapp-business/wa-dev-console/?business_id=376401858423810
meta configuration youtube: https://www.youtube.com/watch?v=3YPeh-3AFmM

Errors:
RuntimeError: Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0.
Solution:
https://stackoverflow.com/questions/76958817/streamlit-your-system-has-an-unsupported-version-of-sqlite3-chroma-requires-sq

### DB Configurations
#### install sqlite3
sudo apt update
sudo apt install sqlite3
sudo apt install libsqlite3-dev
sqlite3 --version

type "sqlite3" in terminal.
now u can run db queries

go to the specic folder where the .DB file exist.
1. Create or connect to db -> sqlite3 example.db
2. show databases -> .databases
3. show tables -> .tables

install sqlitebrowser to get GUI -> $sudo apt install sqlitebrowser

Reference to upload media to whatsapp: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media#supported-media-types
Reference to send message especially pdf: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#media-object 

### AWS



#### run the script in background
nohup sudo ../dtvenv/bin/python -u run.py >> ~/output.log 2>&1 &
ps aux | grep python
sudo kill processid

#### run sql query
Go to the path where the db is located.
Run sudo ../dtvenv/bin/python ../run_sql_query.py 

### Git
Git clear changes and pull branch
sudo git reset --hard
sudo git clean -fd

## DOCKER
### install docker
    sudo apt-get update

    #### Install required packages:
    sudo apt-get install \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    #### Add Docker’s official GPG key:
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    #### Set up the stable repository:
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    #### install docker engine
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io

    #### Start Docker and enable it to start at boot:
    sudo systemctl start docker
    sudo systemctl enable docker

    #### Verify the installation:
    sudo docker run hello-world



    mkdir digital_tourism
    cd digital_tourism

    ### Clone the git repo
    sudo git clone -b gowshi https://github.com/GowshaliniSenz/Whatsapp-chatbot.git
    Note: makesure Dockerfile is there
    ### create docker image
    docker build -t <image name> .
    sudo docker build -t digital_tourism_img .

    ### Run the container
    sudo docker run -d -p 5000:5000 digital_tourism_img   #run the python file in the background
    sudo docker run -p 5000:5000 digital_tourism_img   #run the python file directly


    ### Verify the Container is Running
    sudo docker ps

    ### go inside container 
    sudo docker exec -it 51c0bc3df66a /bin/bash

    ###rm docker image
    sudo docker rmi <img id>

    ###rm stoped containers
    sudo docker container prune


### Langgraph test server
cd ~/digital_tourism/Whatsapp-chatbot/Langraph/project\ DT/
sudo ~/digital_tourism/dtvenv/bin/python run.py 
sudo ~/digital_tourism/dtvenv/bin/python ~/digital_tourism/run_sql_query.py

nohup sudo ~/digital_tourism/dtvenv/bin/python -u run.py >> ~/output.log 2>&1 &











