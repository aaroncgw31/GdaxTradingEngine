# docker build -t ubuntu1604py36
FROM ubuntu:16.04

#install python3.6, git
RUN apt-get update
RUN apt-get install -y software-properties-common vim
RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update

RUN apt-get install -y build-essential python3.6 python3.6-dev python3-pip python3.6-venv
RUN apt-get install -y git
RUN git clone https://aaroncgw:Hunt4Money@bitbucket.org/arbcloud/gdaxtradingengine.git

#install python packages
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel
RUN python3.6 -m pip install psycopg2
RUN python3.6 -m pip install bintrees
RUN python3.6 -m pip install requests
RUN python3.6 -m pip install websocket-client

#set up stunnel
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install stunnel4 -y
RUN apt-get install openssl
RUN apt-get install nano
RUN openssl s_client -showcerts -connect fix-public.sandbox.gdax.com:4198 < /dev/null | openssl x509 -outform PEM > fix-public.sandbox.gdax.com.pem
RUN echo "[Coinbase]" >> /etc/stunnel/stunnel.conf
RUN echo "CAfile = /fix-public.sandbox.gdax.com.pem" >> /etc/stunnel/stunnel.conf
RUN echo "client = yes" >> /etc/stunnel/stunnel.conf
RUN echo "accept = 127.0.0.1:4197" >> /etc/stunnel/stunnel.conf
RUN echo "verify = 4" >> /etc/stunnel/stunnel.conf
RUN echo "connect = fix-public.sandbox.gdax.com:4198" >> /etc/stunnel/stunnel.conf
RUN sed -i "s|ENABLED=0|ENABLED=1 |g" /etc/default/stunnel4
CMD /etc/init.d/stunnel4 restart
CMD ["python3.6", "./gdaxtradingengine/gdaxTradingEngine.py"]
