/****************************************************************************
** Meta object code from reading C++ file 'ResourceTelemetry.h'
**
** Created by: The Qt Meta Object Compiler version 68 (Qt 6.4.2)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../../../apps/fa3-control-center/src/ResourceTelemetry.h"
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'ResourceTelemetry.h' doesn't include <QObject>."
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
struct qt_meta_stringdata_ResourceTelemetry_t {
    uint offsetsAndSizes[56];
    char stringdata0[18];
    char stringdata1[17];
    char stringdata2[1];
    char stringdata3[11];
    char stringdata4[19];
    char stringdata5[23];
    char stringdata6[9];
    char stringdata7[21];
    char stringdata8[11];
    char stringdata9[20];
    char stringdata10[23];
    char stringdata11[6];
    char stringdata12[11];
    char stringdata13[11];
    char stringdata14[11];
    char stringdata15[11];
    char stringdata16[12];
    char stringdata17[13];
    char stringdata18[9];
    char stringdata19[11];
    char stringdata20[17];
    char stringdata21[18];
    char stringdata22[16];
    char stringdata23[13];
    char stringdata24[9];
    char stringdata25[11];
    char stringdata26[14];
    char stringdata27[16];
};
#define QT_MOC_LITERAL(ofs, len) \
    uint(sizeof(qt_meta_stringdata_ResourceTelemetry_t::offsetsAndSizes) + ofs), len 
Q_CONSTINIT static const qt_meta_stringdata_ResourceTelemetry_t qt_meta_stringdata_ResourceTelemetry = {
    {
        QT_MOC_LITERAL(0, 17),  // "ResourceTelemetry"
        QT_MOC_LITERAL(18, 16),  // "telemetryChanged"
        QT_MOC_LITERAL(35, 0),  // ""
        QT_MOC_LITERAL(36, 10),  // "sampleFast"
        QT_MOC_LITERAL(47, 18),  // "sampleAccelerators"
        QT_MOC_LITERAL(66, 22),  // "handleGpuProbeFinished"
        QT_MOC_LITERAL(89, 8),  // "exitCode"
        QT_MOC_LITERAL(98, 20),  // "QProcess::ExitStatus"
        QT_MOC_LITERAL(119, 10),  // "exitStatus"
        QT_MOC_LITERAL(130, 19),  // "handleGpuProbeError"
        QT_MOC_LITERAL(150, 22),  // "QProcess::ProcessError"
        QT_MOC_LITERAL(173, 5),  // "error"
        QT_MOC_LITERAL(179, 10),  // "refreshNow"
        QT_MOC_LITERAL(190, 10),  // "cpuPercent"
        QT_MOC_LITERAL(201, 10),  // "ramPercent"
        QT_MOC_LITERAL(212, 10),  // "ramUsedGiB"
        QT_MOC_LITERAL(223, 11),  // "ramTotalGiB"
        QT_MOC_LITERAL(235, 12),  // "gpuAvailable"
        QT_MOC_LITERAL(248, 8),  // "gpuLabel"
        QT_MOC_LITERAL(257, 10),  // "gpuPercent"
        QT_MOC_LITERAL(268, 16),  // "gpuMemoryUsedGiB"
        QT_MOC_LITERAL(285, 17),  // "gpuMemoryTotalGiB"
        QT_MOC_LITERAL(303, 15),  // "gpuTemperatureC"
        QT_MOC_LITERAL(319, 12),  // "npuAvailable"
        QT_MOC_LITERAL(332, 8),  // "npuLabel"
        QT_MOC_LITERAL(341, 10),  // "npuPercent"
        QT_MOC_LITERAL(352, 13),  // "pressureState"
        QT_MOC_LITERAL(366, 15)   // "pressureSummary"
    },
    "ResourceTelemetry",
    "telemetryChanged",
    "",
    "sampleFast",
    "sampleAccelerators",
    "handleGpuProbeFinished",
    "exitCode",
    "QProcess::ExitStatus",
    "exitStatus",
    "handleGpuProbeError",
    "QProcess::ProcessError",
    "error",
    "refreshNow",
    "cpuPercent",
    "ramPercent",
    "ramUsedGiB",
    "ramTotalGiB",
    "gpuAvailable",
    "gpuLabel",
    "gpuPercent",
    "gpuMemoryUsedGiB",
    "gpuMemoryTotalGiB",
    "gpuTemperatureC",
    "npuAvailable",
    "npuLabel",
    "npuPercent",
    "pressureState",
    "pressureSummary"
};
#undef QT_MOC_LITERAL
} // unnamed namespace

Q_CONSTINIT static const uint qt_meta_data_ResourceTelemetry[] = {

 // content:
      10,       // revision
       0,       // classname
       0,    0, // classinfo
       6,   14, // methods
      15,   62, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       1,       // signalCount

 // signals: name, argc, parameters, tag, flags, initial metatype offsets
       1,    0,   50,    2, 0x06,   16 /* Public */,

 // slots: name, argc, parameters, tag, flags, initial metatype offsets
       3,    0,   51,    2, 0x08,   17 /* Private */,
       4,    0,   52,    2, 0x08,   18 /* Private */,
       5,    2,   53,    2, 0x08,   19 /* Private */,
       9,    1,   58,    2, 0x08,   22 /* Private */,

 // methods: name, argc, parameters, tag, flags, initial metatype offsets
      12,    0,   61,    2, 0x02,   24 /* Public */,

 // signals: parameters
    QMetaType::Void,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int, 0x80000000 | 7,    6,    8,
    QMetaType::Void, 0x80000000 | 10,   11,

 // methods: parameters
    QMetaType::Void,

 // properties: name, type, flags
      13, QMetaType::Double, 0x00015001, uint(0), 0,
      14, QMetaType::Double, 0x00015001, uint(0), 0,
      15, QMetaType::Double, 0x00015001, uint(0), 0,
      16, QMetaType::Double, 0x00015001, uint(0), 0,
      17, QMetaType::Bool, 0x00015001, uint(0), 0,
      18, QMetaType::QString, 0x00015001, uint(0), 0,
      19, QMetaType::Double, 0x00015001, uint(0), 0,
      20, QMetaType::Double, 0x00015001, uint(0), 0,
      21, QMetaType::Double, 0x00015001, uint(0), 0,
      22, QMetaType::Double, 0x00015001, uint(0), 0,
      23, QMetaType::Bool, 0x00015001, uint(0), 0,
      24, QMetaType::QString, 0x00015001, uint(0), 0,
      25, QMetaType::Double, 0x00015001, uint(0), 0,
      26, QMetaType::QString, 0x00015001, uint(0), 0,
      27, QMetaType::QString, 0x00015001, uint(0), 0,

       0        // eod
};

Q_CONSTINIT const QMetaObject ResourceTelemetry::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_meta_stringdata_ResourceTelemetry.offsetsAndSizes,
    qt_meta_data_ResourceTelemetry,
    qt_static_metacall,
    nullptr,
    qt_incomplete_metaTypeArray<qt_meta_stringdata_ResourceTelemetry_t,
        // property 'cpuPercent'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'ramPercent'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'ramUsedGiB'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'ramTotalGiB'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'gpuAvailable'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'gpuLabel'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'gpuPercent'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'gpuMemoryUsedGiB'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'gpuMemoryTotalGiB'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'gpuTemperatureC'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'npuAvailable'
        QtPrivate::TypeAndForceComplete<bool, std::true_type>,
        // property 'npuLabel'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'npuPercent'
        QtPrivate::TypeAndForceComplete<double, std::true_type>,
        // property 'pressureState'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // property 'pressureSummary'
        QtPrivate::TypeAndForceComplete<QString, std::true_type>,
        // Q_OBJECT / Q_GADGET
        QtPrivate::TypeAndForceComplete<ResourceTelemetry, std::true_type>,
        // method 'telemetryChanged'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'sampleFast'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'sampleAccelerators'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'handleGpuProbeFinished'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<int, std::false_type>,
        QtPrivate::TypeAndForceComplete<QProcess::ExitStatus, std::false_type>,
        // method 'handleGpuProbeError'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<QProcess::ProcessError, std::false_type>,
        // method 'refreshNow'
        QtPrivate::TypeAndForceComplete<void, std::false_type>
    >,
    nullptr
} };

void ResourceTelemetry::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<ResourceTelemetry *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->telemetryChanged(); break;
        case 1: _t->sampleFast(); break;
        case 2: _t->sampleAccelerators(); break;
        case 3: _t->handleGpuProbeFinished((*reinterpret_cast< std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<QProcess::ExitStatus>>(_a[2]))); break;
        case 4: _t->handleGpuProbeError((*reinterpret_cast< std::add_pointer_t<QProcess::ProcessError>>(_a[1]))); break;
        case 5: _t->refreshNow(); break;
        default: ;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            using _t = void (ResourceTelemetry::*)();
            if (_t _q_method = &ResourceTelemetry::telemetryChanged; *reinterpret_cast<_t *>(_a[1]) == _q_method) {
                *result = 0;
                return;
            }
        }
    }else if (_c == QMetaObject::ReadProperty) {
        auto *_t = static_cast<ResourceTelemetry *>(_o);
        (void)_t;
        void *_v = _a[0];
        switch (_id) {
        case 0: *reinterpret_cast< double*>(_v) = _t->cpuPercent(); break;
        case 1: *reinterpret_cast< double*>(_v) = _t->ramPercent(); break;
        case 2: *reinterpret_cast< double*>(_v) = _t->ramUsedGiB(); break;
        case 3: *reinterpret_cast< double*>(_v) = _t->ramTotalGiB(); break;
        case 4: *reinterpret_cast< bool*>(_v) = _t->gpuAvailable(); break;
        case 5: *reinterpret_cast< QString*>(_v) = _t->gpuLabel(); break;
        case 6: *reinterpret_cast< double*>(_v) = _t->gpuPercent(); break;
        case 7: *reinterpret_cast< double*>(_v) = _t->gpuMemoryUsedGiB(); break;
        case 8: *reinterpret_cast< double*>(_v) = _t->gpuMemoryTotalGiB(); break;
        case 9: *reinterpret_cast< double*>(_v) = _t->gpuTemperatureC(); break;
        case 10: *reinterpret_cast< bool*>(_v) = _t->npuAvailable(); break;
        case 11: *reinterpret_cast< QString*>(_v) = _t->npuLabel(); break;
        case 12: *reinterpret_cast< double*>(_v) = _t->npuPercent(); break;
        case 13: *reinterpret_cast< QString*>(_v) = _t->pressureState(); break;
        case 14: *reinterpret_cast< QString*>(_v) = _t->pressureSummary(); break;
        default: break;
        }
    } else if (_c == QMetaObject::WriteProperty) {
    } else if (_c == QMetaObject::ResetProperty) {
    } else if (_c == QMetaObject::BindableProperty) {
    }
}

const QMetaObject *ResourceTelemetry::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ResourceTelemetry::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_ResourceTelemetry.stringdata0))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int ResourceTelemetry::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 6)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 6;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 6)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 6;
    }else if (_c == QMetaObject::ReadProperty || _c == QMetaObject::WriteProperty
            || _c == QMetaObject::ResetProperty || _c == QMetaObject::BindableProperty
            || _c == QMetaObject::RegisterPropertyMetaType) {
        qt_static_metacall(this, _c, _id, _a);
        _id -= 15;
    }
    return _id;
}

// SIGNAL 0
void ResourceTelemetry::telemetryChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
