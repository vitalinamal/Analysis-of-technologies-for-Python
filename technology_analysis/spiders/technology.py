import re
from urllib.parse import urljoin

import scrapy
from scrapy.http import Response

from dotenv import load_dotenv
import os

load_dotenv()
technologies = os.getenv("TECHNOLOGIES").split(",")


class TechnologySpider(scrapy.Spider):
    name = "technology"
    allowed_domains = ["www.work.ua"]
    start_urls = [
        "https://www.work.ua/jobs-python/",
        "https://www.work.ua/jobs-python-програміст/",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_urls = set()
        self.technologies = technologies

    def parse(self, response: Response, **kwargs) -> None:
        self.visited_urls.add(response.url)

        vacancy_links = self.get_vacancies(response)
        for link in vacancy_links:
            if link not in self.visited_urls:
                self.visited_urls.add(link)
                yield scrapy.Request(url=link, callback=self.parse_vacancy)

        next_page = response.css(
            "li.add-left-default > a.ga-pagination-default::attr(href)"
        ).get()
        if next_page:
            next_page_url = urljoin(response.url, next_page)
            if next_page_url not in self.visited_urls:
                self.visited_urls.add(next_page_url)
                yield response.follow(next_page_url, callback=self.parse)

    def parse_vacancy(self, response: Response, **kwargs) -> None:
        skills = self.extract_skills(response)
        yield {
            "vacancy_title": response.css("h1#h1-name *::text").getall(),
            "skills": skills,
            "vacancy_url": response.url,
        }

    def extract_skills(self, response: Response, **kwargs) -> list:
        description_parts = response.css(
            "div#job-description.company-description *::text"
        ).getall()
        description_text = " ".join(description_parts).strip()

        listed_skills = response.css(
            "ul.flex.flex-wrap.list-unstyled li span.ellipsis::text"
        ).getall()

        found_skills = []

        for technology in self.technologies:
            if re.search(
                    r'\b' + re.escape(technology) + r'\b[.,\/]*',
                    description_text,
                    re.IGNORECASE
            ):
                found_skills.append(technology)

        extra_skills = [
            skill for skill in listed_skills if skill in self.technologies
        ]
        all_found_skills = list(set(found_skills + extra_skills))
        return all_found_skills

    @staticmethod
    def get_vacancies(response: Response, **kwargs) -> list:
        vacancies = response.css(
            "div#pjax-jobs-list > div[tabindex='0'].card.card-hover.card-"
            "search.card-visited.wordwrap.job-link.js-job-link-blank"
        )
        vacancies_links = []
        for vacancy in vacancies:
            relative_link = vacancy.css('a[tabindex="-1"]::attr(href)').get()
            vacancy_link = urljoin(response.url, relative_link)
            vacancies_links.append(vacancy_link)
        return vacancies_links
