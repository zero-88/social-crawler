import json
import logging
import time
import urllib

import requests
from requests.exceptions import RequestException

from ..exception import CrawlerError, NoResultError
from ..utils import fileUtils, textUtils
from .crawler import ZSCrawler

logger = logging.getLogger(__name__)


class InstagramCrawler(ZSCrawler):

    def __init__(self, dao, searchQuery):
        super(InstagramCrawler, self).__init__(dao, searchQuery)
        self.delay = 5
        self.config = {
            'url': 'https://www.instagram.com',
            'search': {
                'url': 'https://www.instagram.com/web/search/topsearch/?context=user&query={}&count={}',
                'count': 2
            },
            'profile': {
                'url': 'https://www.instagram.com/{}/?__a=1'
            }
        }

    def search0(self, runId):
        logger.info('Instagram Search')
        total, count, errors = 0, 0, []
        maxItem = self.config.get('search').get('count')
        for searchKey in self.keywords:
            for keyword in searchKey.get('keywords'):
                url = self.config.get('search').get('url').format(urllib.quote_plus(keyword), maxItem)
                logger.info('Search in instagram - URL::{}'.format(url))
                try:
                    t, c = self.__search0__(runId=runId, url=url, specialist=searchKey.get('specialist'), keyword=keyword)
                    total += t
                    count += c
                except CrawlerError as e:
                    errors.append({'url': url, 'message': e.message})
        return {'total': total, 'count': count, 'errors': errors}

    def __search0__(self, runId, url, specialist, keyword):
        time.sleep(self.delay)
        try:
            total, count = 0, 0
            response = requests.get(url)
            data = response.json()
            logger.debug(fileUtils.writeTempFile(textUtils.decode(json.dumps(data)), fileUtils.joinPaths(
                'zsc', 'instagram', 'search', 'search_' + keyword + '.json')))
            if data.get('status') != 'ok':
                raise CrawlerError('Instagram URL error', where=url)
            users = data.get('users')
            for user in users:
                total += 1
                profile = user.get('user')
                if profile is None:
                    logger.debug(u'Profile error::{}'.format(user))
                    continue
                entity = {}
                entity['key'] = profile.get('username')
                entity['title'] = profile.get('full_name')
                entity['avatar'] = profile.get('profile_pic_url') or ''
                entity['instagram'] = self.config.get('url') + '/' + profile.get('username')
                entity['specialist'] = specialist
                entity['metadata'] = {'keywords': [keyword]}
                self.processEntity(runId, entity)
                count += 1
            return total, count
        except RequestException as e:
            raise CrawlerError('Instagram URL error', ex=e, where=url)

    def access0(self, runId, records):
        logger.info('Instagram Access')
        total, count, errors = 0, 0, []
        for record in records:
            total += 1
            url = self.config.get('profile').get('url').format(record.get('key'))
            logger.info('Parsing profile::{} in instagram::{}'.format(record.get('key'), url))
            try:
                self.updateEntity(runId=runId, record=record, entity=self.__access0__(url, record.get('key')))
                count += 1
            except (NoResultError, CrawlerError) as e:
                errors.append({'url': url, 'message': e.message})
        self.finish(runId, {'total': total, 'count': count, 'errors': errors})

    def __access0__(self, url, key):
        try:
            response = requests.get(url)
            data = response.json()
            logger.debug(fileUtils.writeTempFile(textUtils.decode(json.dumps(data)), fileUtils.joinPaths(
                'zsc', 'instagram', 'access', 'profile_' + key + '.json')))
            user = data.get('user')
            if user is None:
                raise CrawlerError('Instagram URL error', ex=e, where=url)
            facebook = user.get('connected_fb_page')
            website = user.get('external_url')
            socials = self.findSocials(user.get('biography'))
            if facebook:
                if socials.get('facebook'):
                    socials.get('facebook').append(facebook)
                else:
                    socials['facebook'] = [facebook]
            return {'website': website, 'socials': socials}
        except RequestException as e:
            raise NoResultError('Instagram URL error', ex=e, where=url)
