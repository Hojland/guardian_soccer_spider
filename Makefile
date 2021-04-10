.PHONY: make_requirements, build_local
image_name=docker.pkg.github.com/hojland/guardian_soccer_spider/matchreports

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
		--name ${image_name} \
		--env-file .env \
		${image_name}:latest