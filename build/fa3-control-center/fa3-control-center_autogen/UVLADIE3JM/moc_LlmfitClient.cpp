/****************************************************************************
** Meta object code from reading C++ file 'LlmfitClient.h'
**
** Created by: The Qt Meta Object Compiler version 68 (Qt 6.4.2)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../../../apps/fa3-control-center/src/LlmfitClient.h"
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'LlmfitClient.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 68
#error "This file was generated using the moc from 6.4.2. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
namespace {
struct qt_meta_stringdata_LlmfitClient_t {
    uint offsetsAndSizes[34];
    char stringdata0[13];
    char stringdata1[13];
    char stringdata2[1];
    char stringdata3[12];
    char stringdata4[15];
    char stringdata5[8];
    char stringdata6[16];
    char stringdata7[8];
    char stringdata8[8];
    char stringdata9[11];
    char stringdata10[10];
    char stringdata11[5];
    char stringdata12[11];
    char stringdata13[10];
    char stringdata14[11];
    char stringdata15[7];
    char stringdata16[7];
};
#define QT_MOC_LITERAL(ofs, len) \
    uint(sizeof(qt_meta_stringdata_LlmfitClient_t::offsetsAndSizes) + ofs), len 
Q_CONSTINIT static const qt_meta_stringdata_LlmfitClient_t qt_meta_stringdata_LlmfitClient = {
    {
        QT_MOC_LITERAL(0, 12),  // "LlmfitClient"
        QT_MOC_LITERAL(13, 12),  // "stateChanged"
        QT_MOC_LITERAL(26, 0),  // ""
        QT_MOC_LITERAL(27, 11),  // "dataChanged"
        QT_MOC_LITERAL(39, 14),  // "filtersChanged"
        QT_MOC_LITERAL(54, 7),  // "refresh"
        QT_MOC_LITERAL(62, 15),  // "recommendModels"
        QT_MOC_LITERAL(78, 7),  // "useCase"
        QT_MOC_LITERAL(86, 7),  // "runtime"
        QT_MOC_LITERAL(94, 10),  // "maxContext"
        QT_MOC_LITERAL(105, 9),  // "available"
        QT_MOC_LITERAL(115, 4),  // "busy"
        QT_MOC_LITERAL(120, 10),  // "statusText"
        QT_MOC_LITERAL(131, 9),  // "lastError"
        QT_MOC_LITERAL(141, 10),  // "socketPath"
        QT_MOC_LITERAL(152, 6),  // "system"
        QT_MOC_LITERAL(159, 6)   // "models"
    },
    "LlmfitClient",
    "stateChanged",
    "",
    "dataChanged",
    "filtersChanged",
    "refresh",
    "recommendModels",
    "useCase",
    "runtime",
    "maxContext",
    "available",
    "busy",
    "statusText",
    "lastError",
    "socketPath",
    "system",
    "models"
};
#undef QT_MOC_LITERAL
} // unnamed namespace

Q_CONSTINIT static const uint qt_meta_data_LlmfitClient[] = {

 // content:
      10,       // revision
       0,       // classname
       0,    0, // classinfo
       5,   14, // methods
      10,   55, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       3,       // signalCount

 // signals: name, argc, parameters, tag, flags, initial metatype offsets
       1,    0,   44,    2, 0x06,   11 /* Public */,
       3,    0,   45,    2, 0x06,   12 /* Public */,
       4,    0,   46,    2, 0x06,   13 /* Public */,

 // methods: name, argc, parameters, tag, flags, initial metatype offsets
       5,    0,   47,    2, 0x02,   14 /* Public */,
       6,    3,   48,    2, 0x02,   15 /* Public */,

 // signals: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,

 // methods: parameters
    QMetaType::Void,
    QMetaType::Void, QMetaType::QString, QMetaType::QString, QMetaType::Int,    7,    8,    9,

 // properties: name, type, flags
      10, QMetaType::Bool, 0x00015001, uint(0), 0,
      11, QMetaType::Bool, 0x00015001, uint(0), 0,
      12, QMetaType::QString, 0x00015001, uint(0), 0,
      13, QMetaType::QString, 0x00015001, uint(0), 0,
      14, QMetaType::QString, 0x00015401, uint(-1), 0,
      15, QMetaType::QVariantMap, 0x00015001, uint(1), 0,
      16, QMetaType::QVariantList, 0x00015001, uint(1), 0,
       7, QMetaType::QString, 0x00015001, uint(2), 0,
       8, QMetaType::QString, 0x00015001, uint(2), 0,
       9, QMetaType::Int, 0x00015001, uint(2), 0,

       0        // eod
};

Q_CONSTINIT const QMetaObject LlmfitClient::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_meta_stringdata_LlmfitClient.offsetsAndSizes,
    qt_meta_data_LlmfitClient,
    qt_static_metacall,
    nullptr,
    qt_incomplete_metaTypeArray<qt_meta_stringdata_LlmfitClient_t,
        // property 'available'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'busy'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'statusText'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'lastError'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'socketPath'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'system'
        QtPrivate::TypeAndForceComplete<QVariantMap, std::true_type>,
        // property 'models'
        QtPrivate::TypeAndForceComplete<QVariantList, std::true_type>,
        // property 'useCase'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'runtime'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'maxContext'
        QtPrivate::TypeAndForceComplete<int, std::true_type>,
        // Q_OBJECT / Q_GADGET
        QtPrivate::TypeAndForceComplete<LlmfitClient, std::true_type>,
        // method 'stateChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'dataChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'filtersChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'refresh'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'recommendModels'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<int, std::false_type>
    >,
    nullptr
} };

void LlmfitClient::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<LlmfitClient *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->stateChanged(); break;
        case 1: _t->dataChanged(); break;
        case 2: _t->filtersChanged(); break;
        case 3: _t->refresh(); break;
        case 4: _t->recommendModels((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast< std::add_pointer_t<int>>(_a[3]))); break;
        default: ;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            using _t = void (LlmfitClient::*)();
            if (_t _q_method = &LlmfitClient::stateChanged; *reinterpret_cast<_t *>(_a[1]) == _q_method) {
                *result = 0;
                return;
            }
        }
        {
            using _t = void (LlmfitClient::*)();
            if (_t _q_method = &LlmfitClient::dataChanged; *reinterpret_cast<_t *>(_a[1]) == _q_method) {
                *result = 1;
                return;
            }
        }
        {
            using _t = void (LlmfitClient::*)();
            if (_t _q_method = &LlmfitClient::filtersChanged; *reinterpret_cast<_t *>(_a[1]) == _q_method) {
                *result = 2;
                return;
            }
        }
    }else if (_c == QMetaObject::ReadProperty) {
        auto *_t = static_cast<LlmfitClient *>(_o);
        (void)_t;
        void *_v = _a[0];
        switch (_id) {
        case 0: *reinterpret_cast< bool*>(_v) = _t->available(); break;
        case 1: *reinterpret_cast< bool*>(_v) = _t->busy(); break;
        case 2: *reinterpret_cast< QString*>(_v) = _t->statusText(); break;
        case 3: *reinterpret_cast< QString*>(_v) = _t->lastError(); break;
        case 4: *reinterpret_cast< QString*>(_v) = _t->socketPath(); break;
        case 5: *reinterpret_cast< QVariantMap*>(_v) = _t->system(); break;
        case 6: *reinterpret_cast< QVariantList*>(_v) = _t->models(); break;
        case 7: *reinterpret_cast< QString*>(_v) = _t->useCase(); break;
        case 8: *reinterpret_cast< QString*>(_v) = _t->runtime(); break;
        case 9: *reinterpret_cast< int*>(_v) = _t->maxContext(); break;
        default: break;
        }
    } else if (_c == QMetaObject::WriteProperty) {
    } else if (_c == QMetaObject::ResetProperty) {
    } else if (_c == QMetaObject::BindableProperty) {
    }
}

const QMetaObject *LlmfitClient::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *LlmfitClient::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_LlmfitClient.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int LlmfitClient::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 5)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 5;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 5)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 5;
    }else if (_c == QMetaObject::ReadProperty || _c == QMetaObject::WriteProperty
            || _c == QMetaObject::ResetProperty || _c == QMetaObject::BindableProperty
            || _c == QMetaObject::RegisterPropertyMetaType) {
        qt_static_metacall(this, _c, _id, _a);
        _id -= 10;
    }
    return _id;
}

// SIGNAL 0
void LlmfitClient::stateChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}

// SIGNAL 1
void LlmfitClient::dataChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 1, nullptr);
}

// SIGNAL 2
void LlmfitClient::filtersChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 2, nullptr);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
