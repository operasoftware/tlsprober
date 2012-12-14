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


cat > do_weekly.sh <<-DO_WEEKLY
	cd $PWD/..
	cvs -q up -Pd
	rm results/*
	python weekly_run.py > weekly_run.log
DO_WEEKLY

cat > do_analyze.sh <<-DO_ANALYZE
	cd $PWD
	if [[ \`ps x | grep bash | grep perform_analyze | wc -l\` -eq 0 ]]
	then
		bash perform_analyze.sh
	fi
DO_ANALYZE


cat > do_analyze2.sh <<-DO_ANALYZE
	cd $PWD
	if [[ \`ps x | grep bash | grep perform_analyz2 | wc -l\` -eq 0 ]]
	then
		bash perform_analyz2.sh
	fi
DO_ANALYZE

cat > do_analyze_a.sh <<-DO_ANALYZE
	cd $PWD
	if [[ \`ps x | grep bash | grep perform_analyz_a | wc -l\` -eq 0 ]]
	then
		bash perform_analyz_a.sh
	fi
DO_ANALYZE


cat > do_analyze2_a.sh <<-DO_ANALYZE
	cd $PWD
	if [[ \`ps x | grep bash | grep perform_analyz_2a| wc -l\` -eq 0 ]]
	then
		bash perform_analyz_2a.sh
	fi
DO_ANALYZE



cat >weekly_crontab1 <<-CRONTAB
	MAILTO=root
	# TLS Prober run  
	0 1 * * 1	bash $PWD/do_weekly.sh > /dev/null
	0,3,5,7,10,13,15,17,20,23,25,27,30,33,35,37,40,42,45,47,50,53,55,57 * * * *	bash $PWD/do_analyze.sh > /dev/null
	0,3,5,7,10,13,15,17,20,23,25,27,30,33,35,37,40,42,45,47,50,53,55,57 * * * *     bash $PWD/do_analyze2.sh > /dev/null
	0,12,24,36,48 * * * *	bash $PWD/do_analyze_a.sh > /dev/null
	6,18,30,42,54 * * * *   bash $PWD/do_analyze2_a.sh > /dev/null
CRONTAB

crontab weekly_crontab1
