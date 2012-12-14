#   Copyright 2010-2012 Opera Software ASA 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


mkdir ../work
git clone --recursive -b master -o temp $1 ../work/tlsprober-testbase2

cat > start_node.sh <<-START_NODE
	export HOSTNAME=$HOSTNAME
	cd $PWD/..
 	if [[ \`ps x | grep python | grep cluster_manager.py | wc -l\` > 0 ]]
 	then
 	   exit;
 	fi	
 	if [[ \`ps x | grep python | grep cluster_start.py | wc -l\` > 0 ]]
 	then
 	   exit;
 	fi	
	git pull
	git checkout master
	git submodule update --recursive
		
	python cluster_manager.py > cluster_node.log
START_NODE

cat > start_test_node2.sh <<-START_NODE
	export HOSTNAME=$HOSTNAME
	cd $PWD/../work/tlsprober-testbase2
 	if [[ \`ps x | grep python | grep cluster_manager.py | wc -l\` > 0 ]]
 	then
 	   exit;
 	fi	
 	if [[ \`ps x | grep python | grep cluster_start.py | wc -l\` > 0 ]]
 	then
 	   exit;
 	fi	
	git pull
	git checkout master
	git submodule update --recursive	
	python cluster_manager.py --testbase2 > cluster_node.log
START_NODE

cat >node_crontab1 <<-CRONTAB
	MAILTO=root
	# TLS Prober run  
	0,10,20,30,40,50 * * * *	bash $PWD/start_node.sh >/dev/null
	5,15,25,35,45,55 * * * *	bash $PWD/start_test_node2.sh >/dev/null
CRONTAB

crontab node_crontab1
