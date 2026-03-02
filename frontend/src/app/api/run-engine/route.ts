import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import util from 'util';

const execPromise = util.promisify(exec);

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const startDate = body.startDate; // YYYY-MM-DD

        if (!startDate) {
            return NextResponse.json({ error: 'Falta startDate' }, { status: 400 });
        }

        const scriptsPath = '/home/pablo/Documentos/gestion-centro/scripts/python';

        // 1. Ejecutar el Undo condicionado a la fecha
        const undoCmd = `python3 undo_menu_marzo.py ${startDate}`;
        const { stdout: stdoutUndo, stderr: stderrUndo } = await execPromise(undoCmd, { cwd: scriptsPath });

        console.log("UNDO OUT:", stdoutUndo);
        if (stderrUndo) console.error("UNDO ERR:", stderrUndo);

        // 2. Ejecutar el Motor IA condicionado a la fecha
        const motorCmd = `python3 motor_asignaciones_supabase.py --start-date ${startDate}`;
        const { stdout: stdoutMotor, stderr: stderrMotor } = await execPromise(motorCmd, { cwd: scriptsPath });

        console.log("MOTOR OUT:", stdoutMotor);
        if (stderrMotor) console.error("MOTOR ERR:", stderrMotor);

        return NextResponse.json({
            success: true,
            message: 'Motor de Inteligencia Artificial finalizado.',
            undoLogs: stdoutUndo,
            motorLogs: stdoutMotor
        });

    } catch (error: any) {
        console.error("Critical Error Executing Python:", error);
        return NextResponse.json({ error: error.message || 'Error de invocación a Shell' }, { status: 500 });
    }
}
