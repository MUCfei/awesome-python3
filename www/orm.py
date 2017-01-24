import asyncio, logging
import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' %(sql))

@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        charset = kw.get('charset', 'utf-8'),
        autocommit = kw.get('autocommit', True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        loop = loop       
    )
    
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchchall()
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs
        
@asyncio.coroutine
def execute(sql, args):
    log(sql, args)
    with (yield from __pool)as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args or ())
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        return affected
        
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
     
    # 以','为分隔符，将列表合成字符串
    return (','.join(L))
'''       
class Model(dict, metaclass = ModelMetaclass):
    
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)
        
    def __setattr__(self, key, value):
        self[key] = value
     
    def getValue(self, key):
        return getattr(self, key, None)
    
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else fidld.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
'''       
class Field(object):
    
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
        
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
# -*- 定义不同类型的衍生Field -*-
# -*- 表的不同列的字段的类型不一样
 

class BooleanField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'boolean', False, default)
 
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False,  default=0):
        super().__init__(name, 'bigint', primary_key, default)
 
class FloatField(Field):
    def __init__(self, name=None, primary_key=False,  default=0.0):
        super().__init__(name, 'real', primary_key, default)
         
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'Text', False, default)
class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None,ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)
    
class ModelMetaclass(type):
    
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return  type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f:'`%s`' % f, fields))
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) value (%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__updata__'] = 'update `%s` set %s where `%s`=?' % (tableName, ','.join(map(lambda f:'`%s`' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
        
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
 
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'"Model" object has no attribute：%s' %(key))
 
    def __setattr__(self, key, value):
        self[key] = value
 
    def getValue(self, key):
        # 内建函数getattr会自动处理
        return getattr(self, key, None)
 
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if not value:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' %(key, str(value)))
                setattr(self, key, value)
        return value
 
 
 
    @classmethod
    # 类方法有类变量cls传入，从而可以用cls做一些相关的处理。并且有子类继承时，调用该类方法时，传入的类变量cls是子类，而非父类。
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        '''find objects by where clause'''
        sql = [cls.__select__]
         
        if where:
            sql.append('where')
            sql.append(where)
         
        if args is None:
            args = []
         
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
 
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' %str(limit))
        rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]
 
     
    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        '''find number by select and where.'''
        sql = ['select %s __num__ from `%s`' %(selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']
     
 
    @classmethod
    @asyncio.coroutine
    def find(cls, primarykey):
        '''find object by primary key'''
        rs = yield from select('%s where `%s`=?' %(cls.__select__, cls__primary_key__), [primarykey], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])
 
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' %rows)
 
    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__updata__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' %rows)
 
    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__updata__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' %rows)
 
 
 
if __name__ == '__main__':
     
    class User(Model):
        # 定义类的属性到列的映射：
        id = IntegerField('id',primary_key=True)
        name = StringField('username')
        email = StringField('email')
        password = StringField('password')
 
    # 创建一个实例：
    u = User(id=12345, name='peic', email='peic@python.org', password='password')
    # 保存到数据库：
    u.save()
    print(u)        
    
    
    
    
    
    
    
    
    
    
    
        
    
    
    
    
    
    
    
    