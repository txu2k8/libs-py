## **Elastic Search**
[![](https://img.shields.io/badge/Project-ES-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

ElasticSearch related test

#### Install
    pip install tlib

#### Usage
```
# See the TestCase in *_stress.py / *_index.py ...
Such as:
def test_stress(self):
    """Elasticsearch Stress Test"""
    logger.info(self.test_stress.__doc__)

    es_stress_obj = ElasticsearchStress(
        ES_ADDRESS, ES_USERNAME, ES_PASSWORD, ES_PORT, CA_FILE, NO_VERIFY_CERTS,
        NUMBER_OF_INDICES, NUMBER_OF_DOCUMENTS, NUMBER_OF_CLIENTS,
        NUMBER_OF_SECONDS, NUMBER_OF_SHARDS, NUMBER_OF_REPLICAS, BULK_SIZE,
        MAX_FIELDS_PER_DOCUMENT, MAX_SIZE_PER_FIELD, CLEANUP,
        STATS_FREQUENCY, WAIT_FOR_GREEN, index_name='es_stress')
    es_stress_obj.run()

# How to run in this project
    python run_test.py es -h
        usage: run_test.py es [-h] {index,stress} ...
        positional arguments:
          {index,stress}  ES index/stress
            index         ES index args
            stress        ES index

    python run_test.py es stress -h
        Test Case List:
          NO. CaseName                   CaseDescription
          1   stress                     es index stress test
          2   cleanup                    delete exist index

```

***
[1]: https://txu2008.github.io