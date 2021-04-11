.PHONY: make_requirements, build_local
PWD := $(shell pwd)
CUR_DIR := $(notdir ${PWD})
image_name=docker.pkg.github.com/hojland/guardian_soccer_spider/matchreports

docker_login:
	@echo "Requesting credentials for docker login"
	@$(eval export GITHUB_ACTOR=Hojland)
	@$(eval export GITHUB_TOKEN=$(shell awk -F "=" '/GITHUB_TOKEN/{print $$NF}' .make.env))
	@docker login https://docker.pkg.github.com/$(GITHUB_ACTOR)/ -u $(GITHUB_ACTOR) -p $(GITHUB_TOKEN)

make_requirements:
	poetry export -f requirements.txt -o requirements.txt

test_spider:
	scrapy runspider src/spider.py -o 's3://${BUCKET_NAME}/scraping/feeds/%(name)s.jl:jl

build_local:
	docker build -t ${image_name}:latest --build-arg PROD_ENV=$(env) -f Dockerfile .

start_spider:
	make docker_login
	docker run \
		-d \
		-it \
		-v ${PWD}/matchreports/.scrapy:/app/matchreports/.scrapy \
		--name ${CUR_DIR} \
		--env-file .env \
		${image_name}:latest \
		"scrapy crawl guardian-match-reports"

insert_crontab:
	$(eval CRONJOB=0 18 * * * cd ${PWD} && make start_spider)
	( crontab -l ; echo "${CRONJOB}" ) | crontab -