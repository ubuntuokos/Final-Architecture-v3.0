/****************************************************************************
** Meta object code from reading C++ file 'McpControlService.h'
**
** Created by: The Qt Meta Object Compiler version 68 (Qt 6.4.2)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../../../apps/fa3-control-center/src/McpControlService.h"
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'McpControlService.h' doesn't include <QObject>."
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
struct qt_meta_stringdata_McpControlService_t {
    uint offsetsAndSizes[20];
    char stringdata0[18];
    char stringdata1[8];
    char stringdata2[1];
    char stringdata3[18];
    char stringdata4[9];
    char stringdata5[19];
    char stringdata6[5];
    char stringdata7[7];
    char stringdata8[16];
    char stringdata9[9];
};
#define QT_MOC_LITERAL(ofs, len) \
    uint(sizeof(qt_meta_stringdata_McpControlService_t::offsetsAndSizes) + ofs), len 
Q_CONSTINIT static const qt_meta_stringdata_McpControlService_t qt_meta_stringdata_McpControlService = {
    {
        QT_MOC_LITERAL(0, 17),  // "McpControlService"
        QT_MOC_LITERAL(18, 7),  // "targets"
        QT_MOC_LITERAL(26, 0),  // ""
        QT_MOC_LITERAL(27, 17),  // "authoritySnapshot"
        QT_MOC_LITERAL(45, 8),  // "targetId"
        QT_MOC_LITERAL(54, 18),  // "createDraftRequest"
        QT_MOC_LITERAL(73, 4),  // "mode"
        QT_MOC_LITERAL(78, 6),  // "prompt"
        QT_MOC_LITERAL(85, 15),  // "attachmentsJson"
        QT_MOC_LITERAL(101, 8)   // "riskHint"
    },
    "McpControlService",
    "targets",
    "",
    "authoritySnapshot",
    "targetId",
    "createDraftRequest",
    "mode",
    "prompt",
    "attachmentsJson",
    "riskHint"
};
#undef QT_MOC_LITERAL
} // unnamed namespace

Q_CONSTINIT static const uint qt_meta_data_McpControlService[] = {

 // content:
      10,       // revision
       0,       // classname
       0,    0, // classinfo
       3,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       0,       // signalCount

 // methods: name, argc, parameters, tag, flags, initial metatype offsets
       1,    0,   32,    2, 0x102,    1 /* Public | MethodIsConst  */,
       3,    1,   33,    2, 0x102,    2 /* Public | MethodIsConst  */,
       5,    5,   36,    2, 0x102,    4 /* Public | MethodIsConst  */,

 // methods: parameters
    QMetaType::QVariantList,
    QMetaType::QVariantMap, QMetaType::QString,    4,
    QMetaType::QVariantMap, QMetaType::QString, QMetaType::QString, QMetaType::QString, QMetaType::QString, QMetaType::QString,    6,    4,    7,    8,    9,

       0        // eod
};

Q_CONSTINIT const QMetaObject McpControlService::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_meta_stringdata_McpControlService.offsetsAndSizes,
    qt_meta_data_McpControlService,
    qt_static_metacall,
    nullptr,
    qt_incomplete_metaTypeArray<qt_meta_stringdata_McpControlService_t,
        // Q_OBJECT / Q_GADGET
        QtPrivate::TypeAndForceComplete<McpControlService, std::true_type>,
        // method 'targets'
        QtPrivate::TypeAndForceComplete<QVariantList, std::false_type>,
        // method 'authoritySnapshot'
        QtPrivate::TypeAndForceComplete<QVariantMap, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        // method 'createDraftRequest'
        QtPrivate::TypeAndForceComplete<QVariantMap, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>,
        QtPrivate::TypeAndForceComplete<const QString &, std::false_type>
    >,
    nullptr
} };

void McpControlService::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<McpControlService *>(_o);
        (void)_t;
        switch (_id) {
        case 0: { QVariantList _r = _t->targets();
            if (_a[0]) *reinterpret_cast< QVariantList*>(_a[0]) = std::move(_r); }  break;
        case 1: { QVariantMap _r = _t->authoritySnapshot((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast< QVariantMap*>(_a[0]) = std::move(_r); }  break;
        case 2: { QVariantMap _r = _t->createDraftRequest((*reinterpret_cast< std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[3])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[4])),(*reinterpret_cast< std::add_pointer_t<QString>>(_a[5])));
            if (_a[0]) *reinterpret_cast< QVariantMap*>(_a[0]) = std::move(_r); }  break;
        default: ;
        }
    }
}

const QMetaObject *McpControlService::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *McpControlService::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_McpControlService.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int McpControlService::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 3)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 3;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 3)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 3;
    }
    return _id;
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
