# -*- coding: utf-8 -*-
import os
import json
import logging
import xml.etree.ElementTree as ET
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from django.conf import settings
from ..models import Process, Error

